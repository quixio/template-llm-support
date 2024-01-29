import quixstreams as qx
import os
from datetime import timedelta

import redis
from redis.commands.json.path import Path

# redis connection
r = redis.Redis(
  host=os.environ["redis_host"],
  port=int(os.environ["redis_port"]),
  password=os.environ["redis_pwd"]
)

client = qx.KafkaStreamingClient(os.environ["broker_address"])
topic_consumer = client.get_topic_consumer(os.environ["input"])

def on_stream_recv_handler(sc: qx.StreamConsumer):
    # prefix key with project id to avoid collisions between projects.
    key = os.environ["Quix__Workspace__Id"] + ":" + sc.stream_id
    
    def on_data_recv_handler(stream_consumer: qx.StreamConsumer, data: qx.TimeseriesData):
        for ts in data.timestamps:
            # delete conversation from redis when the customer terminates the conversation.
            if "good bye" in ts.parameters["text"].string_value.lower():
                r.delete(key)
                print(f"Deleted key {key} from redis")
                return

            entry = {
                "timestamp": ts.timestamp_milliseconds,
                "text": ts.parameters["text"].string_value,
                "role": ts.parameters["role"].string_value,
                "sentiment": ts.parameters["sentiment"].numeric_value,
                "average_sentiment": ts.parameters["average_sentiment"].numeric_value,
                "conversation_id": ts.parameters["conversation_id"].string_value,
                "agent_id": ts.parameters["agent_id"].numeric_value,
                "agent_name": ts.parameters["agent_name"].string_value,
                "customer_id": ts.parameters["customer_id"].numeric_value if "customer_id" in ts.parameters else 0,
                "customer_name": ts.parameters["customer_name"].string_value if "customer_name" in ts.parameters else "",
            }

            cached = r.json().get(key)

            if not cached:
                cached = []
                print("New key = {}".format(key))

            # store messages in the conversation as a list of json objects
            cached.append(entry)
            r.json().set(key, Path.root_path(), cached)
            r.expire(key, timedelta(minutes=float(os.environ["expire_after"])))

            print("updated key: {}".format(key))
    
    sc.timeseries.on_data_received = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()