import os
import time
import uuid
import random
from pathlib import Path

# Import the main Quix Streams module for data processing and transformation:
from quixstreams import Application

# Import the supplimentary Quix Streams modules for interacting with Kafka: 
from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder, TopicCreationConfigs
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer, SerializationContext
# (see https://quix.io/docs/quix-streams/v2-0-latest/api-reference/quixstreams.html for more details)

# Import a Hugging Face utility to download models directly from Hugging Face hub:
from huggingface_hub import hf_hub_download

# Imports Langchain modules for managing prompts and conversation chains:
from langchain.llms import LlamaCpp
from langchain.prompts import load_prompt
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory
from langchain.schema import SystemMessage

# Create a constant that defines the role of the bot:
AGENT_ROLE = "agent"

# Set the current role to the role constant:
role = AGENT_ROLE
chat_id = ""

# Download the model and save it to the service's state directory if it is not already there:
model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)

if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

# Load the model with the apporiate parameters:
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

system_message_content = "You are a customer of a large electronics retailer called 'ACME electronics' who is trying to resolve an issue with a defective product that you purchased."

model = Llama2Chat(llm=llm,
                system_message=SystemMessage(
                    content=system_message_content)
)

# Defines how much of the conversation history to give to the model
# during each exchange (300 tokens, or a little over 300 words)
# Function automatically prunes the oldest messages from conversation history that fall outside the token range.
memory = ConversationTokenBufferMemory(
    llm=llm,
    max_token_limit=300,
    ai_prefix= "AGENT",
    human_prefix= "CUSTOMER",
    return_messages=True
)

# Initializes a conversation chain and loads the prompt template from a YAML file 
# i.e "You are a support agent and need to answer the customer...".
chain = ConversationChain(llm=model, prompt=load_prompt("prompt.yaml"), memory=memory)

# Initializes a Quix Kafka consumer with a consumer group based on the role
# and configured to read the latest message if no offset was previously registered for the consumer group
app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")

# Defines the input and output topics with the relevant deserialization and serialization methods (and get the topic names from enviroiment variables)

input_topic = app.topic(os.environ["topic"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["topic"], value_serializer=QuixTimeseriesSerializer())

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)


# Load a list of possible agent names from a text file:
def agents_init():
    out = []

    with open("agents.txt", "r") as fd:
        for a in fd:
            if a:
                out.append(a.strip())
    return out

agents = agents_init()

# Initialize the chat conversation with the customer agent
def chat_init():
    chat_id = str(uuid.uuid4()) # Give the conversation an ID for effective message keying
    agent_id = random.getrandbits(16) # Give the agent a random ID to display in the dashboard
    agent_name = random.choice(agents) # Randomly select a name from the list of agent names
    first_name = agent_name.split(' ')[0] # Extract just the first name for the initial greeting

    # Use a standard greeting rather than an AI generated one to kick off the conversation
    greet = f"""Hello, welcome to ACME Electronics support, my name is {first_name}. 
               How can I help you today?"""

    # Load the relevant configurations from environment variables
    ### In Quix Cloud, These variables are already preconfigured with defaults
    ### When running locally, you need to define 'Quix__Sdk__Token' as an environment variable
    ### Defining 'Quix__Workspace__Id' is also preferable, but often the workspace ID can be inferred.
    cfg_builder = QuixKafkaConfigsBuilder()

    # Get the input topic name from an environment variable
    cfgs, topics, _ = cfg_builder.get_confluent_client_configs([os.environ["topic"]])

    # Create the topic if it doesn't yet exist
    cfg_builder.create_topics([TopicCreationConfigs(name=topics[0])])

    # Define a serializer for adding the extra headers
    serializer = QuixTimeseriesSerializer()

    # Add the chat_id as an extra header so that we can use to partition the different conversation streams
    headers = {**serializer.extra_headers, "uuid": chat_id}

    # Define a dictionary for the message values
    value = {
        "role": role,
        "text": greet,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "conversation_id": chat_id,
        "Timestamp": time.time_ns(),
    }

    # Initialize a Kafka Producer using the chat ID as the message key
    with Producer(broker_address=cfgs.pop("bootstrap.servers"), extra_config=cfgs) as producer:
        producer.produce(
            topic=topics[0],
            headers=headers,
            key=chat_id,
            value=serializer(value=value, ctx=SerializationContext(topic=topics[0], headers=headers)),
        )

    print("Started chat")

chat_init()


# Define a function to reply to the customer's messages
def reply(row: dict):
    print(f"Replying to: {row['text']}")

    # The customer bot is primed to say "good bye" if the conversation has lasted too long
    # message limit defined in "conversation_length" environment variable
    # The agent looks for this "good bye" so it knows to restart too.

    # Send the customers response to the conversation chain so that the agent LLM can generate a reply
    # and store that reply in the msg variable
    msg = chain.run(row["text"])

    print(f"{role.upper()}: {msg}\n")

    # Replace previous role and text values of the row so that it can be sent back to Kafka as a new message
    # containing the agents role and reply 

# Filter the SDF to include only incoming rows where the roles that dont match the bot's current role
# So that it doesn't reply to its own messages
sdf = sdf[sdf["role"] != role]

# Trigger the reply function for any new messages(rows) detected in the filtered SDF
sdf = sdf.apply(reply, stateful=False)

# Check the SDF again and filter out any empty rows
sdf = sdf[sdf.apply(lambda row: row is not None)]

# Update the timestamp column to the current time in nanoseconds
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

# Publish the processed SDF to a Kafka topic specified by the output_topic object. 
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)