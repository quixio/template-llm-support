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



