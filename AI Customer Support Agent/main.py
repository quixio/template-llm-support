import os
import time
from quixstreams import Application
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer

app = Application.Quix("test", auto_offset_reset="latest")
input_topic = app.topic(os.environ["topic"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["topic"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(topic=input_topic)

def stream_init():
    sdf["message"] = "Hello, world!"
    sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

    sdf.to_topic(output_topic)

stream_init()

# update timestamp
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)