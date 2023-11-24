import os, sys
import quixstreams as qx
import pandas as pd
from pathlib import Path
from llama_cpp import Llama
from datetime import datetime
from huggingface_hub import hf_hub_download

role = os.environ["role"].lower()
if role != "agent" and role != "customer":
    print("Error: invalid role {}".format(role))
    sys.exit(1)

model_name = "llama-2-7b-chat.Q4_K_M.gguf"
model_path = "./state/{}".format(model_name)

if not Path(model_path).exists():
    print("The model path does not exist in state. Downloading model...")
    hf_hub_download("TheBloke/Llama-2-7b-Chat-GGUF", model_name, local_dir="state")
else:
    print("Loading model from state...")

llm = Llama(model_path)

client = qx.QuixStreamingClient()
topic_producer = client.get_topic_producer(os.environ["topic"])
topic_consumer = client.get_topic_consumer(os.environ["topic"])

product = os.environ["product"]
scenario = """
            The following transcript represents a converstation between you, a 
            customer support agent who works for a large electronics retailer called 
            'ACME electronics', and a customer who has bought a defective {} and 
            wants to understand what their options are for resolving the issue. 
            Please continue the conversation, but only reply as AGENT:""".format(product)

def on_stream_recv_handler(sc: qx.StreamConsumer):
    print("Received stream {}".format(sc.stream_id))

    def on_data_recv_handler(_: qx.StreamConsumer, df: pd.DataFrame):
        sender = df["role"][0].upper()
        if sender != role:
            msg = df["text"][0]
            print("{}: {}".format(sender, msg))
            reply = ""
            print("{}: {}".format(role, reply))
            
            data = {
                "timestamp": [datetime.utcnow()],
                "role": [role], 
                "text": [reply], 
                "conversation_id": ["002"]
            }
            sp = topic_producer.get_or_create_stream(sc.stream_id)
            sp.timeseries.buffer.publish(pd.DataFrame(data))

    sc.timeseries.on_dataframe_received = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()