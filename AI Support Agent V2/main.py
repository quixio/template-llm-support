import os
import time
import random
from pathlib import Path

# Import the main Quix Streams module for data processing and transformation
from quixstreams import Application, State

# Import the supplimentary Quix Streams modules for interacting with Kafka: 
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
# (see https://quix.io/docs/quix-streams/v2-0-latest/api-reference/quixstreams.html for more details)

# Import a Hugging Face utility to download models directly from Hugging Face hub:
from huggingface_hub import hf_hub_download

# Import Langchain modules for managing prompts and conversation chains:
from langchain.llms import LlamaCpp
from langchain.prompts import load_prompt
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory

# Initialite variables for supplementary customer metadata:
role = "agent"
customer_id = 0
customer_name = ""

# Download the model and save it to the service's state directory if it is not already there:
model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)

if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

# Function to load a list of values from a text file
def get_list(file: str):
    list = []

    with open(file, "r") as fd:
        for p in fd:
            if p:
                list.append(p.strip())
    return list

# Loads a list of possible names, products and moods 
# from their respective text files for random selection later on
names = get_list("names.txt")

# Initialize the chat conversation with the support agent
def chain_init():
    # Loads the prompt template from a YAML file 
    # i.e "You are a customer support agent interacting with a customer..."
    prompt = load_prompt("prompt.yaml")

    # randomly select the AI agents name
    prompt.partial_variables["name"] = random.choice(names)

    # For debugging, print the prompt with the populated mood and product variables.
    print("Prompt:\n{}".format(prompt.to_json()))

    # Load the model with the apporiate parameters
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

    # Defines how much of the conversation history to give to the model
    # during each exchange (300 tokens, or a little over 300 words)
    # Function automatically prunes the oldest messages from conversation history that fall outside the token range.
    memory = ConversationTokenBufferMemory(
        llm=llm,
        max_token_limit=300,
        ai_prefix="AGENT",
        human_prefix="CUSTOMER",
        return_messages=True
    )

    return ConversationChain(llm=model, prompt=prompt, memory=memory)

# hold the conversation chains
chains = {}

# Initialize a Quix Kafka consumer with a consumer group based on the role
# and configured to read the latest message if no offset was previously registered for the consumer group
app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")

# Define the input and output topics with the relevant deserialization and serialization methods
input_topic = app.topic(os.environ["topic"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["topic"], value_serializer=QuixTimeseriesSerializer())

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(input_topic)

# Define a function to reply to the messages
def reply(row: dict, state: State):
    global customer_id, customer_name

    if row["conversation_id"] not in chains:
        chains[row["conversation_id"]] = chain_init()

    # Replace previous role with the new role
    row["role"] = role

    print(f"Replying to: {row['text']}\n")
    
    print("Generating response...\n")
    msg = chains[row["conversation_id"]].run(row["text"])
    print(f"{role.upper()}: {msg}\n")

    row["text"] = msg

    return row

# Filter the SDF to include only incoming rows where the roles that dont match the bot's current role
# So that it doesn't reply to its own messages
sdf = sdf[sdf["role"] != role]

# Trigger the reply function for any new messages(rows) detected in the filtered SDF
# while enabling stateful storage (required for tracking conversation length)
sdf = sdf.apply(reply, stateful=True)

# Check the SDF again and filter out any empty rows
sdf = sdf[sdf.apply(lambda row: row is not None)]

# Update the timestamp column to the current time in nanoseconds
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)