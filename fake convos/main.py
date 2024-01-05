import quixstreams as qx
import time
import datetime
import math
import os


# Quix injects credentials automatically to the client. 
# Alternatively, you can always pass an SDK token manually as an argument.
client = qx.QuixStreamingClient()

# Open the output topic where to write data out
topic_producer = client.get_topic_producer(topic_id_or_name = os.environ["output"])

# Set stream ID or leave parameters empty to get stream ID generated.
stream = topic_producer.create_stream()

    #  "role": role,
    #     "text": greet,
    #     "agent_id": agent_id,
    #     "agent_name": agent_name,
    #     "conversation_id": chat_id,
    #     "Timestamp": time.time_ns(),

#Yes it's a smart toilet purchased from the Beyond Insanity bathroom appliances store

stream.timeseries \
    .buffer \
    .add_timestamp(datetime.datetime.utcnow()) \
    .add_value("text", "Yes I have the invoice. I will email it to you. The problem is, when I flush goldfish and carp, I expect the toilet to cook them to perfection before flushing them to our dining table. Instead they are being flushed to the bedroom closet.") \
    .add_value("conversation_id", "abc123") \
    .add_value("role", "customer") \
    .add_value("customer_name", "James") \
    .add_value("customer_id", "123456789") \
    .publish()

print("Closing stream")
stream.close()