import os
from pathlib import Path
from datetime import datetime

import quixstreams as qx

from huggingface_hub import hf_hub_download

from langchain.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain_experimental.chat_models import Llama2Chat
from langchain.memory import ConversationTokenBufferMemory

CHAT_ID = "002"
AGENT_ROLE = "agent"

role = AGENT_ROLE
chat_id = CHAT_ID

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
    ai_prefix= "agent",
    human_prefix= "customer",
    return_messages=True
)

# Loading conversation from file
product = os.environ["product"]
tone = os.environ["tone"]

with open('prompt_template.txt', 'r') as file:
    loaded_prompt = file.read()

# define a custom PromptTemplate that supports the new variables such as mood and product
class CustomPromptTemplate(StringPromptTemplate):
    # Define more variables here as needed.
    tone: str
    product: str
    template: str

    def format(self, **kwargs) -> str:
        kwargs['tone']=self.tone
        kwargs['product'] = self.product
        return self.template.format(**kwargs)


# Feeding the PromptTemplate with the new variables
PROMPT = CustomPromptTemplate(input_variables=["history", "input"], template=loaded_prompt, tone=tone,product=product)

chain = ConversationChain(llm=model, prompt=PROMPT, memory=memory)

client = qx.QuixStreamingClient()
topic_producer = client.get_topic_producer(os.environ["topic"])
topic_consumer = client.get_topic_consumer(os.environ["topic"])

def chat_init():
    greet = "Hello, welcome to ACME Electronics support, my name is Percy. How can I help you today?"
    msg = qx.TimeseriesData()
    msg.add_timestamp(datetime.utcnow()) \
       .add_value("role", role) \
       .add_value("text", greet) \
       .add_value("conversation_id", chat_id)

    sp = topic_producer.get_or_create_stream("conversation_{}".format(chat_id))
    sp.timeseries.publish(msg)

def on_stream_recv_handler(sc: qx.StreamConsumer):
    print("Received stream {}".format(sc.stream_id))

    def on_data_recv_handler(_: qx.StreamConsumer, data: qx.TimeseriesData):
        ts = data.timestamps[0]
        sender = ts.parameters["role"].string_value
        if sender != role:
            msg = ts.parameters["text"].string_value
            print("{}: {}".format(sender, msg))

            if "good bye" in msg.lower():
                print("Initializing a new conversation...")
                memory.clear()
                chat_init()
                return

            print("Generating response...")
            reply = chain.run(msg)
            print("{}: {}".format(role, reply))
            
            td = qx.TimeseriesData()
            td.add_timestamp(datetime.utcnow()) \
              .add_value("role", role) \
              .add_value("text", reply) \
              .add_value("conversation_id", chat_id)

            sp = topic_producer.get_or_create_stream(sc.stream_id)
            sp.timeseries.publish(td)

    buf = sc.timeseries.create_buffer()
    buf.packet_size = 1
    buf.on_data_released = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

chat_init()

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()
