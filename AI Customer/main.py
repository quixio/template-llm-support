from llama_cpp import Llama
import os
import json
import pandas as pd
from datetime import datetime
from huggingface_hub import hf_hub_download
from pathlib import Path


import os
from quixstreams import Application, State, message_key
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from draft_producer import DraftProducer

print("HI ", end="")
print("HI ", end="")
print("HI ", end="")
print("HI ", end="")

app = Application.Quix("transformation-v6", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["output"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())
draft_producer = DraftProducer(os.environ["draft_topic"])


file_path = Path('./state/llama-2-7b-chat.Q4_K_M.gguf')
REPO_ID = "TheBloke/Llama-2-7b-Chat-GGUF"
FILENAME = "llama-2-7b-chat.Q4_K_M.gguf"

if not file_path.exists():
    # perform action if the file does not exist
    print('The model path does not exist in state. Downloading model...')
    hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir="state")
else:
    print('The model has been detected in state. Loading model from state...')

llm = Llama(model_path="./state/llama-2-7b-chat.Q4_K_M.gguf")

product = os.environ["product"]
scenario = f"The following transcript represents a conversation between you, a customer of a large electronics retailer called 'ACME electronics', and a support agent who you are contacting to resolve an issue with a defective {product} you purchased. Your goal is try and understand what your options are for resolving the issue. Please continue the conversation, but only reply as CUSTOMER:"

convostore = "conversation.json"

if os.path.exists(convostore):
    os.remove(convostore)
    print(f"The file {convostore} has been deleted.")
else:
    print(f"The file {convostore} does not exist yet.")

sdf = app.dataframe(input_topic)

def generate_response(row, prompt, max_tokens=250, temperature=0.7, top_p=0.95, repeat_penalty=1.2, top_k=150):
    
    draft_producer.produce(row, message_key())
    print("LETMESEE")
    
    result = llm(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stream=True,
        stop=["AGENT:","CUSTOMER:","\n"],
        repeat_penalty=repeat_penalty,
        top_k=top_k,
        echo=True
    )


    response = ""
    for iteration in result:
        iteration_text = iteration["choices"][0]["text"]
        response += iteration_text
        row["chat-message"] = response
        row["draft"] = True
        draft_producer.produce(row, message_key())
        print(iteration_text, end='')

    return response
    
def update_conversation(row, text, role, conversation_id, filename="conversation.json"):
    """
    Update the conversation history stored in a JSON file.

    Parameters:
        prompt (str): The prompt for the AI model, including the conversation history.
        role (str): The role of the agent (e.g., "customer" or "support_agent").
        conversation_id (str): The ID of the conversation.
        filename (str): The name of the file where the conversation history is stored.

    Returns:
        str: The generated reply.
    """
    # Read the existing conversation history from the file
    try:
        with open(filename, 'r') as file:
            conversation_history = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file does not exist or is empty, initialize an empty list
        conversation_history = []

    # Include the conversation history as part of the prompt
    full_history = "\n".join([f"{msg['TAG__name'].upper()}: {msg['chat-message']}" for msg in conversation_history])
    prompt = scenario + '\n\n' + full_history + f'\nAGENT:{text}' + '\nCUSTOMER:'

    # Generate the reply using the AI model
    print("Thinking about my response....")
    reply = generate_response(row, prompt)  # This function should be defined elsewhere to handle the interaction with the AI model
    finalreply = reply.replace(prompt, ' ').replace('{', '').replace('}', '').replace('"', '').strip()
    print(f"My reply was '{finalreply}'")
    # Create a dictionary for the reply
    reply_dict = {
        "TAG__name": role.upper(),
        "TAG__room": conversation_id,
        "chat-message": finalreply,
    }

    print(reply_dict)

    # Append the reply dictionary to the conversation history
    conversation_history.append(reply_dict)

    # Write the updated conversation history back to the file
    with open(filename, 'w') as file:
        json.dump(conversation_history, file)

    # Return the generated reply
    return finalreply

print("Listening for messages...")
counter = 0

def get_answer(row: dict):
    print(f"\n------\nRESPONDING T0: {row['chat-message']} \n------\n")
    custreply = update_conversation(row, {row['chat-message']}, "customer", message_key() , convostore)
    print(custreply)
    #publish_rp(custreply)
    print("I have sent my reply to the agent.")

def call_llm(row: dict, callback):

    result = llm(row["chat-message"])


    

    return result

sdf = sdf[sdf["Tags"].contains("name")]
# Here put transformation logic.
sdf = sdf[sdf["Tags"]["name"] == "agent"]

sdf = sdf.apply(get_answer)

sdf = sdf.update(lambda row: print(row))

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)



