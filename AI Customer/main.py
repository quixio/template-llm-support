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
from llm_bot import LlmBot

app = Application.Quix("transformation-v8", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["output"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())
draft_producer = DraftProducer(os.environ["draft_topic"])

product = os.environ["product"]
scenario = f"The following transcript represents a conversation between you, a customer of a large electronics retailer called 'ACME electronics', and a support agent who you are contacting to resolve an issue with a defective {product} you purchased. Your goal is try and understand what your options are for resolving the issue. Please continue the conversation, but only reply as CUSTOMER:"

llm_bot = LlmBot(product, scenario)


sdf = app.dataframe(input_topic)

print("Listening for messages...")
counter = 0

def get_answer(row: dict, state: State):
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
    print(f"\n------\nRESPONDING T0: {row['chat-message']} \n------\n")

    row["Tags"]["name"] = "customer"

    conversation_history = state.get("state_key", [])

    # Include the conversation history as part of the prompt
    full_history = "\n".join([f"{row['Tags']['name'].upper()}: {msg}" for msg in conversation_history])
    prompt = scenario + '\n\n' + full_history + f'\nAGENT:{row["chat-message"]}' + '\nCUSTOMER:'

    # Generate the reply using the AI model
    print("Thinking about my response....")
    reply = generate_response(row, prompt)  # This function should be defined elsewhere to handle the interaction with the AI model
    print(reply)
    finalreply = reply.replace(prompt, ' ').replace('{', '').replace('}', '').replace('"', '').strip()
    
    print(f"My reply was '{finalreply}'")
    # Create a dictionary for the reply

    conversation_history.append(finalreply)
    print(conversation_history)

    state.set(state_key, conversation_history)

    # Return the generated reply
    row["chat-message"] = finalreply


    return row




sdf = sdf[sdf["Tags"].contains("name")]
# Here put transformation logic.
sdf = sdf[sdf["Tags"]["name"] == "agent"]


sdf = sdf.apply(get_answer, stateful=True)

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)



