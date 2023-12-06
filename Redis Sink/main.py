import quixstreams as qx
import os

import redis
from redis.commands.json.path import Path

r = redis.Redis(
  host=os.environ["redis_host"],
  port=int(os.environ["redis_port"]),
  password=os.environ["redis_pwd"]
)

client = qx.QuixStreamingClient()
topic_consumer = client.get_topic_consumer(topic_id_or_name = os.environ["input"])

def on_stream_recv_handler(sc: qx.StreamConsumer):
    
    def on_data_recv_handler(stream_consumer: qx.StreamConsumer, data: qx.TimeseriesData):
        for ts in data.timestamps:
            entry = {
                "text": ts.parameters["text"].string_value,
                "role": ts.parameters["role"].string_value,
                "sentiment": ts.parameters["sentiment"].numeric_value,
                "conversation_id": ts.parameters["conversation_id"].string_value
            }

            cached = r.json().get(sc.stream_id)
            if not cached:
                cached = []

            cached.append(entry)
            r.json().set(sc.stream_id, Path.root_path(), cached)
            print("saved: \n{}".format(cached))
    
    sc.timeseries.on_data_received = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()