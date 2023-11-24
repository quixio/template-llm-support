import os, sys
from pathlib import Path
from datetime import datetime

import quixstreams as qx
from huggingface_hub import hf_hub_download

from langchain.llms import LlamaCpp
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory

AGENT_ROLE = "agent"
CUSTOMER_ROLE = "customer"
CONVERSATION_ID = "002"

conversation_id = CONVERSATION_ID
role = os.environ["role"].lower()

if role != AGENT_ROLE and role != CUSTOMER_ROLE:
    print("Error: invalid role {}".format(role))
    sys.exit(1)

model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)
if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

llm = LlamaCpp(model_path=model_path, streaming=False)
model = Llama2Chat(llm=llm)
memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=300, return_messages=True)
chain = ConversationChain(llm=model, memory=memory)

client = qx.QuixStreamingClient()
topic_producer = client.get_topic_producer(os.environ["topic"])
topic_consumer = client.get_topic_consumer(os.environ["topic"])

product = os.environ["product"]

def on_stream_recv_handler(sc: qx.StreamConsumer):
    print("Received stream {}".format(sc.stream_id))

    def on_data_recv_handler(_: qx.StreamConsumer, data: qx.TimeseriesData):
        ts = data.timestamps[0]
        sender = ts.parameters["role"].string_value
        if sender != role:
            msg = ts.parameters["text"].string_value
            print("{}: {}".format(sender, msg))
            reply = chain.run(msg)
            print("{}: {}".format(role, reply))
            
            td = qx.TimeseriesData()
            td.add_timestamp(datetime.utcnow()) \
              .add_value("role", role) \
              .add_value("text", reply) \
              .add_value("conversation_id", conversation_id)

            sp = topic_producer.get_or_create_stream(sc.stream_id)
            sp.timeseries.publish(td)

    buf = sc.timeseries.create_buffer()
    buf.packet_size = 1
    buf.on_data_released = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

if role == AGENT_ROLE:
    greeting = "Hello, welcome to ACME Electronics support, my name is Percy. How can I help you today?"

    msg = qx.TimeseriesData()
    msg.add_timestamp(datetime.utcnow()) \
       .add_value("role", role) \
       .add_value("text", greeting) \
       .add_value("conversation_id", conversation_id)
    
    sp = topic_producer.get_or_create_stream("conversation_{}".format(conversation_id))
    sp.timeseries.publish(msg)

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()