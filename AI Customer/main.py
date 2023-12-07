import os
from quixstreams import Application, State, message_key
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from llm_bot import LlmBot
from draft_producer import DraftProducer
import time

role = os.environ["role"]


app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")

input_topic = app.topic(os.environ["output"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

draft_producer = DraftProducer(os.environ["draft_topic"])

state_key = "conversation-history-v2"
director_prompt_state_key = "director_prompt_state_key-v1"

product = os.environ["product"]
scenario = os.environ["scenario"].format(product)

llm_bot = LlmBot(product, scenario, draft_producer)


sdf = app.dataframe(input_topic)

def chain_init():
    prompt = load_prompt("prompt.yaml")
    prompt.partial_variables["mood"] = random.choice(moods)
    prompt.partial_variables["product"] = random.choice(products)

    print("Prompt:\n{}".format(prompt.to_json()))

    llm = LlamaCpp(
        model_path=model_path,
        max_tokens=250,
        top_p=0.95,
        top_k=150,
        temperature=0.7,
        repeat_penalty=1.2,
        n_ctx=2048,
        streaming=False
    )

    model = Llama2Chat(llm=llm)

    memory = ConversationTokenBufferMemory(
        llm=llm,
        max_token_limit=300,
        ai_prefix= "CUSTOMER",
        human_prefix= "AGENT",
        return_messages=True
    )

    return ConversationChain(llm=model, prompt=prompt, memory=memory)


print("Listening for messages...")
counter = 0

def get_answer(row: dict, state: State):
    
    print(f"\n------\nRESPONDING T0: {row['chat-message']} \n------\n")

    row["Tags"]["name"] = role

    conversation_history = state.get(state_key, [])
    full_history = "\n".join([f"{msg['TAG__name'].upper()}: {msg['chat-message']}" for msg in conversation_history])

    prompt = scenario + '\n\n'
    prompt += full_history[-400:] 
    prompt += f'\nAGENT:{row["chat-message"]}'
    prompt +=  director_prompt_state if role == "agent" else "" 
    prompt += f'\n{role.upper()}:'

    print(prompt)

    # Generate the reply using the AI model
    print("Thinking about my response....")
    reply = llm_bot.generate_response(row, prompt, bytes.decode(message_key()))  # This function should be defined elsewhere to handle the interaction with the AI model
    finalreply = reply.replace(prompt, ' ').replace('{', '').replace('}', '').replace('"', '').strip()
    
    reply_dict = {
        "TAG__name": role.upper(),
        "TAG__room": bytes.decode(message_key()),
        "chat-message": finalreply,
    }

    print(f"My reply was '{finalreply}'")
    # Create a dictionary for the reply

    conversation_history.append(reply_dict)

    state.set(state_key, conversation_history)

    # Return the generated reply
    row["chat-message"] = finalreply


        return row


sdf = sdf[sdf["Tags"]["name"] != role]

sdf = sdf.apply(get_answer, stateful=True)
sdf = sdf[sdf.apply(lambda row: row is not None)]

sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)



