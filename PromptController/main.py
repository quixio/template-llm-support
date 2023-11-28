import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
import time

app = Application.Quix("prompt-controller-v1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)


sdf = sdf[sdf.contains("average_sentiment_count")]

sdf = sdf.update(lambda value: value.update({
    'Timestamp': time.time_ns(),
    'role': 'director'
    }))





sdf = sdf[sdf["average_sentiment"] < -0.5 and sdf["average_sentiment_count"] > 3]
sdf["chat-message"] = "The sentiment of this conversation is very negative, can you increase politeness?"

sdf = sdf.update(lambda row: print(row))



sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)