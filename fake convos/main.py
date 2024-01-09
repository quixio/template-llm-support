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

## customer

# stream.timeseries \
#     .buffer \
#     .add_timestamp(datetime.datetime.utcnow()) \
#     .add_value("text", "Hi I'm Steve, I have a problem with my air conditioning that im very frustrated about") \
#     .add_value("conversation_id", "abc123") \
#     .add_value("role", "customer") \
#     .add_value("customer_name", "James") \
#     .add_value("customer_id", "123456789") \
#     .publish()


## agent
# value = {
#         "role": role,
#         "text": greet,
#         "agent_id": agent_id,
#         "agent_name": agent_name,
#         "conversation_id": chat_id,
#         "Timestamp": time.time_ns(),
#     }
stream.timeseries \
    .buffer \
    .add_timestamp(datetime.datetime.utcnow()) \
    .add_value("text", "Hi Im Steve, your friendly ACME customer support agent, how may I serve you on this fine day?") \
    .add_value("conversation_id", "FOO_112") \
    .add_value("role", "agent") \
    .add_value("agent_name", "Steve") \
    .add_value("agent_id", "999") \
    .publish()




print("Closing stream")
stream.close()