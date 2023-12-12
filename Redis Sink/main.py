import quixstreams as qx
import os
from datetime import timedelta

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
    print("Received new stream: " + sc.stream_id)

    key = os.environ["Quix__Workspace__Id"] + ":" + sc.stream_id
    
    def on_data_recv_handler(stream_consumer: qx.StreamConsumer, data: qx.TimeseriesData):
        print("Recv data, key={}, len={}".format(key, len(data.timestamps)))

        for ts in data.timestamps:
            entry = {
                "timestamp": ts.timestamp_milliseconds,
                "text": ts.parameters["text"].string_value,
                "role": ts.parameters["role"].string_value,
                "sentiment": ts.parameters["sentiment"].numeric_value,
                "average_sentiment": ts.parameters["average_sentiment"].numeric_value,
                "conversation_id": ts.parameters["conversation_id"].string_value
            }

            cached = r.json().get(key)
            if not cached:
                cached = []

            cached.append(entry)
            r.json().set(key, Path.root_path(), cached)
            r.expire(key, timedelta(minutes=float(os.environ["expire_after"])))

            print("updated key: {}".format(key))

    def stream_closed_handler(_: qx.StreamConsumer, end: qx.StreamEndType):
        r.delete(key)
        print("Removed conversation {} from cache", sc.stream_id)
    
    sc.timeseries.on_data_received = on_data_recv_handler
    sc.on_stream_closed = stream_closed_handler

topic_consumer.on_stream_received = on_stream_recv_handler

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()