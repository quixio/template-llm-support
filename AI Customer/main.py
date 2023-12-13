import os
import time
import random
from pathlib import Path

from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer

from huggingface_hub import hf_hub_download

from langchain.llms import LlamaCpp
from langchain.prompts import load_prompt
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory

CUSTOMER_ROLE = "customer"

role = CUSTOMER_ROLE
customer_id = 0
customer_name = ""
chat_maxlen = int(os.environ["conversation_length"]) // 2

model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)

if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

def get_list(file: str):
    list = []

    with open(file, "r") as fd:
        for p in fd:
            if p:
                list.append(p.strip())
    return list

names = get_list("names.txt")
moods = get_list("moods.txt")
products = get_list("products.txt")

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

chain = chain_init()

app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")
input_topic = app.topic(os.environ["topic"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["topic"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)

def reply(row: dict, state: State):
    global chain, customer_id, customer_name

    if not "customer_name" in row:
        customer_id = random.getrandbits(16)
        customer_name = random.choice(names)
        row["customer_id"] = customer_id
        row["customer_name"] = customer_name

    row["role"] = role

    if not state.exists("chatlen"):
        state.set("chatlen", 0)

    chatlen = state.get("chatlen")
    print("Debug: chat length = {}".format(chatlen))
    
    if chatlen >= chat_maxlen:
        print("Maximum conversation length reached, ending conversation...")
        chain = chain_init()
        state.set("chatlen", 0)

        row["text"] = "Noted, I think I have enough information. Thank you for your assistance. Good bye!"
        return row

    print("Replying to: {}\n".format(row["text"]))
    
    print("Generating response...\n")
    msg = chain.run(row["text"])
    print("{}: {}\n".format(role.upper(), msg))

    row["text"] = msg
    state.set("chatlen", chatlen + 1)
    return row

sdf = sdf[sdf["role"] != role]
sdf = sdf.apply(reply, stateful=True)
sdf = sdf[sdf.apply(lambda row: row is not None)]

sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)