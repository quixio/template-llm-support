import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from transformers import pipeline

classifier = pipeline('sentiment-analysis')

app = Application.Quix("sentiment-analysis-v2", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
#output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())



                # Calculate "sentiment" feature using label for sign and score for magnitude
                #df.loc[i, "sentiment"] = row["score"] if row["label"] == "POSITIVE" else - row["score"]

                # Add average sentiment (and update memory)
                #self.count = self.count + 1
                #self.sum = self.sum + df.loc[i, "sentiment"]
                #df.loc[i, "average_sentiment"] = self.sum/self.count


sdf = app.dataframe(input_topic)

sdf["sentiment"] = sdf["chat-message"].apply(lambda value: classifier(value))
sdf["sentiment"] = sdf.apply(lambda row: float(row["sentiment"]["score"]) if row["sentiment"]["label"] == "POSITIVE" else -float(row["sentiment"]["score"]))
# Here put transformation logic.

sdf = sdf.update(lambda row: print(row))

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)