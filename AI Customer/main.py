import os
import time
import random
import uuid
import re
from pathlib import Path
import pickle

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
from langchain.schema import SystemMessage
from llama_cpp import llama_log_set
import ctypes


# Create a constant that defines the role of the bot.
CUSTOMER_ROLE = "customer"

# Set the current role to the role constant and initialite variables for supplementary customer metadata:
role = CUSTOMER_ROLE
customer_id = 0
customer_name = ""

# Define the maxiumum number of exchanges so that we can end the conversation if it has gone on too long
# This maximum is defined in an environment variable
# The maxium is divided by two because we are only accounting for the
# customer's side of the conversation
chat_maxlen = int(os.environ["conversation_length"]) // 2

# load the model from state or download it from hugging face
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

# update the moods.txt file to affect the tone of the conversation.
moods = get_list("moods.txt")

# update the products.txt file to add/remove defective appliances.
products = get_list("products.txt")

# Loads the prompt template from a YAML file 
# i.e "You are a customer interacting with a support agent..."
prompt = load_prompt("prompt.yaml")

# Load the model with the apporiate parameters
llm = LlamaCpp(
    model_path=model_path,
    max_tokens=250,
    top_p=0.95,
    top_k=150,
    temperature=0.7,
    repeat_penalty=1.2,
    n_ctx=2048,
    streaming=True
)

# create the Llama model and set the default message
model = Llama2Chat(
    llm=llm,
    system_message=SystemMessage(content="You are a customer of a large electronics retailer called 'ACME electronics' who is trying to resolve an issue with a defective product that you purchased."))

# disable verbose logging
def my_log_callback(level, message, user_data):
    pass
log_callback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(my_log_callback)
llama_log_set(log_callback, ctypes.c_void_p())

# hold the conversation chains
chains = {}

# Initialize a Quix Kafka consumer with a consumer group based on the role
# and configured to read the latest message if no offset was previously registered for the consumer group
app = Application.Quix("transformation-v20-"+role, auto_offset_reset="latest")

# Define the input and output topics with the relevant deserialization and serialization methods
input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["input"], value_serializer=QuixTimeseriesSerializer())

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(input_topic)

# Detect and remove any common text issues from the models response
def clean_text(msg):
    msg = re.sub('^[^:]*:\n?', '', msg, 1)  # Removing any extra "meta commentary" that the LLM sometime adds, followed by a colon.
    msg = re.sub(r'"', '', msg)  # Strip out any speech marks that the LLM tends to add.
    return msg

# Define a function to reply to the agent's messages
def reply(row: dict, state: State):

    try:
    
        # use the conversation id to identify the conversation memory pickle file
        conversation_id = row["conversation_id"]

        is_new_conversation = False
        if "is_new_conversation" in row:
            is_new_conversation = row["is_new_conversation"] or 'False'

        print(f"Is new convo = {is_new_conversation}")

        if is_new_conversation == 'True':
            # randomly select the tone of voice that the customer speaks with
            # (for variation in sentiment analysis)
            # and the specific product that they are calling about
            mood = random.choice(moods)
            prompt.partial_variables["mood"] = mood
            product = random.choice(products)
            prompt.partial_variables["product"] = product

            # add the mood to the data set, just so we can display it in the streamlit dash
            row["customer_mood"] = mood
            
            # add the product to the data set, just so we can display it in the streamlit dash
            row["customer_product"] = product

            # generate customer information randomly.
            customer_id = random.getrandbits(16)
            customer_name = random.choice(names)
            row["customer_id"] = customer_id
            row["customer_name"] = customer_name

            # For debugging, print the prompt with the populated mood and product variables.
            print("Prompt:\n{}".format(prompt.to_json()))
        else:
            row["is_new_conversation"] = 'False'


        pickled_conversation_key = "pickled_conversation-v1"# + conversation_id
        print(f"Getting pickled convo from shared state with key = {pickled_conversation_key}...")
        pickled_convo_state = state.get(pickled_conversation_key, None)
        if pickled_convo_state != None:
            print("Convo found in shared state. Loading...")
            # Convert the string back to pickled bytes
            pickled_bytes = pickled_convo_state.encode('latin1')
            # Unpickle the bytes object
            unpickled_convo_state = pickle.loads(pickled_bytes)
            
            memory = unpickled_convo_state
            print("Done loading")
        else:
            print("No convo found in shared state")
            memory = ConversationTokenBufferMemory(
                    llm=llm,
                    max_token_limit=250,
                    ai_prefix= "CUSTOMER",
                    human_prefix= "AGENT",
                    return_messages=True
                )

        # Initializes a conversation chain and loads the prompt template from a YAML file 
        # i.e "You are a customer of...".
        conversation = ConversationChain(llm=model, prompt=prompt, memory=memory)

        # Replace previous role with the new role
        row["role"] = role
        
        # create a new key to store the length of the conversation 
        # as the number of chat messages
        chatlen_key = "chatlen"

        # If the key doesnt already exist in state, use the Quix state function
        # to add it (so we can keep track of the number of chat exchanges) 
        if not state.exists(chatlen_key):
            state.set(chatlen_key, 0)

        # for debugging, print the current contents of the chatlen_key from state:
        chatlen = state.get(chatlen_key)
        print(f"Chat length = {chatlen}")
        
        # End the conversation if it has gone on too long using the chat_maxlen limit defined
        # at the start of the file
        if chatlen >= chat_maxlen:
            # if the lenth of conversation exceeds the limit, terminate it and dispose the conversation chain.
            print("Maximum conversation length reached, ending conversation...")

            #print(f"Looking for {conversation_id} in chains..")
            if conversation_id in chains:
                print(f"Deleting {conversation_id} from chains..")
                del chains[conversation_id]
                state.delete(chatlen_key)

            # Send a message to the agent with the special termination signal "Good bye"
            # so that the agent knows to "hang up" too
            row["text"] = "Noted, I think I have enough information. Thank you for your assistance. Good bye!"
            return row

        print("Generating response...\n")

        # call the Llama model.
        # this generates the new message and
        # and adds it to the conversation chain
        msg = conversation.run(row["text"])
        msg = clean_text(msg)  # Clean any unnecessary text that the LLM tends to add
        row["text"] = msg

        # persist the chat length to state
        state.set(chatlen_key, chatlen + 1)

        print(f"Pickling convo to shared state with key = {pickled_conversation_key}...")
        # pickle the convo memory object
        pickled_convo = pickle.dumps(conversation.memory)
        # Convert pickled bytes to a string
        pickled_string = pickled_convo.decode('latin1')
        # save the pickled and stringified conversation memory to state
        state.set(pickled_conversation_key, pickled_string)
        print("...done")

        return row

    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(e)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# Filter the SDF to include only incoming rows where the roles that dont match the bot's current role
# So that it doesn't reply to its own messages
sdf = sdf[sdf["role"] != role]

# exclude rows with none as the role. these are conversations that have ended.
sdf = sdf[sdf["role"] != "none"]

sdf = sdf.update(lambda row: print("-----------------------------------\n GOT THIS NEW ROW! \n------------------------------------------"))
sdf = sdf.update(lambda row: print(row))
sdf = sdf.update(lambda row: print("-----------------------------------"))

# Trigger the reply function for any new messages(rows) detected in the filtered SDF
# while enabling stateful storage (required for tracking conversation length)
sdf = sdf.apply(reply, stateful=True)

# Check the SDF again and filter out any empty rows
sdf = sdf[sdf.apply(lambda row: row is not None)]

# Update the timestamp column to the current time in nanoseconds
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

sdf = sdf.update(lambda row: print(f'Replying with: {row["text"]}'))

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)
