from llama_cpp import Llama
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
from quixstreams import Application, State, message_key
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from llm_bot import LlmBot
from draft_producer import DraftProducer

app = Application.Quix("transformation-v9", auto_offset_reset="latest")

input_topic = app.topic(os.environ["output"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())
draft_producer = DraftProducer(os.environ["draft_topic"])
state_key = "conversation-history-v1"

product = os.environ["product"]
scenario = os.environ["scenario"]
role = os.environ["role"]

llm_bot = LlmBot(product, scenario, draft_producer)


sdf = app.dataframe(input_topic)

print("Listening for messages...")
counter = 0

def get_answer(row: dict, state: State):
    
    print(f"\n------\nRESPONDING T0: {row['chat-message']} \n------\n")

    row["Tags"]["name"] = role

    conversation_history = state.get(state_key, [])

    # Include the conversation history as part of the prompt
    full_history = "\n".join([f"{row['Tags']['name'].upper()}: {msg}" for msg in conversation_history])
    prompt = scenario + '\n\n' + full_history[-500:] + f'\nAGENT:{row["chat-message"]}' + '\n{role.upper()}:'

    # Generate the reply using the AI model
    print("Thinking about my response....")
    reply = llm_bot.generate_response(row, prompt, bytes.decode(message_key()))  # This function should be defined elsewhere to handle the interaction with the AI model
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
sdf = sdf[sdf["Tags"]["name"] == role]


sdf = sdf.apply(get_answer, stateful=True)

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)



