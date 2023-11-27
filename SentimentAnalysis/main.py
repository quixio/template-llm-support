import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from transformers import pipeline

classifier = pipeline('sentiment-analysis')

app = Application.Quix("sentiment-analysis-v4", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
#output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())



                # Calculate "sentiment" feature using label for sign and score for magnitude
                #df.loc[i, "sentiment"] = row["score"] if row["label"] == "POSITIVE" else - row["score"]

                # Add average sentiment (and update memory)
                #self.count = self.count + 1
                #self.sum = self.sum + df.loc[i, "sentiment"]
                #df.loc[i, "average_sentiment"] = self.sum/self.count

storage_key = "mean_v1"

def mean(row: dict, state: State):
    mean_state = state.get(storage_key, [])

    mean_state.append(row["sentiment"])

    if len(mean_state) > 5:
        mean_state = mean_state[-5:]

    state.set(storage_key, mean_state)

    return sum(mean_state) / len(mean_state)

sdf = app.dataframe(input_topic)

sdf["sentiment"] = sdf["chat-message"].apply(lambda value: classifier(value)[0])
sdf["sentiment"] = sdf.apply(lambda row: float(row["sentiment"]["score"]) if row["sentiment"]["label"] == "POSITIVE" else -float(row["sentiment"]["score"]))



sdf["average_sentiment"] = sdf.apply(mean, stateful=True)

# Here put transformation logic.

sdf = sdf.update(lambda row: print(row))

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)