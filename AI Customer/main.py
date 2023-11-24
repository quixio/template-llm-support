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


app = Application.Quix("transformation-v1", auto_offset_reset="latest")

output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())



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

def generate_response(prompt, max_tokens=250, temperature=0.7, top_p=0.95, repeat_penalty=1.2, top_k=150):
    response = llm(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stop=["AGENT:","CUSTOMER:","\n"],
        repeat_penalty=repeat_penalty,
        top_k=top_k,
        echo=True
    )

    return response["choices"][0]["text"]

def update_conversation(text, role, conversation_id, filename="conversation.json"):
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
    reply = generate_response(prompt)  # This function should be defined elsewhere to handle the interaction with the AI model
    finalreply = reply.replace(prompt, ' ').replace('{', '').replace('}', '').replace('"', '').strip()
    print(f"My reply was '{finalreply}'")
    # Create a dictionary for the reply
    reply_dict = {
        "TAG__name": role.upper(),
        "TAG__room": conversation_id,
        "chat-message": finalreply,
    }

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
    custreply = update_conversation({row['chat-message']}, "customer", message_key() , convostore)
    print(custreply)
    #publish_rp(custreply)
    print("I have sent my reply to the agent.")

sdf = app.dataframe(output_topic)
def call_llm(row: dict, callback):

    result = llm(row["chat-message"])


    response = ""
    for iteration in result:
        response += iteration
        row["chat-message"] = response
        row["draft"] = True
        sdf._produce(output_topic.name, row, message_key())
        print(iteration, end='')
    

    return response


# Here put transformation logic.
sdf = sdf[sdf["Tags"]["name"] == "agent"]

sdf = sdf.apply(get_answer)

sdf = sdf.update(lambda row: print(row))

draft_sdf = sdf[sdf["draft"] == True]

messages_sdf = sdf[sdf["draft"] == False]

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(draft_sdf, messages_sdf)



