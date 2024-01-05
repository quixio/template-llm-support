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

stream.timeseries \
    .buffer \
    .add_timestamp(datetime.datetime.utcnow()) \
    .add_value("text", "hi i'm Steve") \
    .add_value("conversation_id", "abc123") \
    .publish()

print("Closing stream")
stream.close()