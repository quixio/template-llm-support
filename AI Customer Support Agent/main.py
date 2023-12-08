import os
import uuid
import random
from pathlib import Path
from datetime import datetime

from quixstreams import Application, State
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
    agents = []

    with open("agents.txt", "r") as fd:
        for a in fd:
            if a:
                agents.append(a.strip())
    return agents

agents = agents_init()

def chat_init():
    agent = random.choice(agents)
    greet = """Hello, welcome to ACME Electronics support, my name is {}. 
               How can I help you today?""".format(agent)

    sdf["role"] = role
    sdf["text"] = greet
    sdf["conversation_id"] = str(uuid.uuid4())

    sdf.to_topic(output_topic)

def on_stream_recv_handler(sc: qx.StreamConsumer):
    print("Received stream {}".format(sc.stream_id))

    def on_data_recv_handler(_: qx.StreamConsumer, data: qx.TimeseriesData):
        ts = data.timestamps[0]
        sender = ts.parameters["role"].string_value
        if sender != role:
            msg = ts.parameters["text"].string_value
            print("{}: {}\n".format(sender.upper(), msg))

            if "good bye" in msg.lower():
                print("Initializing a new conversation...")
                memory.clear()
                chat_init()
                return

            print("Generating response...")
            
            reply = chain.run(msg)
            print("{}: {}\n".format(role.upper(), reply))
            
            td = qx.TimeseriesData()
            td.add_timestamp(datetime.utcnow()) \
              .add_value("role", role) \
              .add_value("text", reply) \
              .add_value("conversation_id", ts.parameters["conversation_id"].string_value)

            sp = topic_producer.get_or_create_stream(sc.stream_id)
            sp.timeseries.publish(td)

    buf = sc.timeseries.create_buffer()
    buf.packet_size = 1
    buf.on_data_released = on_data_recv_handler

sdf = sdf[sdf["role"] != role]
sdf = sdf.apply(reply, stateful=True)
sdf = sdf[sdf.apply(lambda row: row is not None)]

sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)
    chat_init()