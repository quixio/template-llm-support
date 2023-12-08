import os
import time
import uuid
import random
from pathlib import Path

from quixstreams import Application
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer

from huggingface_hub import hf_hub_download

from langchain.llms import LlamaCpp
from langchain.prompts import load_prompt
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory

AGENT_ROLE = "agent"
role = AGENT_ROLE

model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)

if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

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
    ai_prefix= "AGENT",
    human_prefix= "CUSTOMER",
    return_messages=True
)

chain = ConversationChain(llm=model, prompt=load_prompt("prompt.yaml"), memory=memory)

app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")
input_topic = app.topic(os.environ["topic"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["topic"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(topic=input_topic)

def agents_init():
    out = []

    with open("agents.txt", "r") as fd:
        for a in fd:
            if a:
                out.append(a.strip())
    return out

agents = agents_init()

def chat_init():
    agent = random.choice(agents)
    greet = """Hello, welcome to ACME Electronics support, my name is {}. 
               How can I help you today?""".format(agent)

    sdf["role"] = role
    sdf["text"] = greet
    sdf["conversation_id"] = str(uuid.uuid4())

    sdf.to_topic(output_topic)
    print("Started chat")

chat_init()

def reply(row: dict):
    print("Replying to: {}".format(row["text"]))
    
    if "good bye" in row["text"].lower():
        print("Initializing a new conversation...")
        memory.clear()
        chat_init()
        return

    print("Generating response...")
    msg = chain.run(row["text"])
    print("{}: {}\n".format(role.upper(), msg))
    
    row["role"] = role
    row["text"] = msg
    return row

sdf = sdf[sdf["role"] != role]
sdf = sdf.apply(reply, stateful=False)
sdf = sdf[sdf.apply(lambda row: row is not None)]

sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    chat_init()
    print("sent message")
    app.run(sdf)