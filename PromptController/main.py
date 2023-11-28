import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer


app = Application.Quix("prompt-controller-v1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)


sdf = sdf[sdf["average_sentiment_count"].notnull()]


sdf = sdf.update(lambda row: print(f"average_sentiment: {row['average_sentiment']}, count: {row['average_sentiment_count']}"))


sdf = sdf[sdf["average_sentiment"] < -0.5 & sdf["average_sentiment_count"] > 3]




sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)