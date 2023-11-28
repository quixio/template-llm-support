import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
import time

app = Application.Quix("prompt-controller-v1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

state_key = "state-v1"

sdf = app.dataframe(input_topic)
sdf = sdf[sdf["Tags"]["name"] != "director"]

sdf = sdf[sdf.contains("average_sentiment_count")]

def update_row(row: dict, state: State):
    row['Timestamp']: time.time_ns()
    row['Tags']['name'] = "director"

    state_value = state.get(state_key, 0)

    if state_value > 0:
        print("Already sent")
        row["chat-message"] = "SENT"
        return row
    else:
        state.set(state_key, 1)
        print("Sent")
        return row



sdf = sdf[sdf["average_sentiment"] < -0.5 and sdf["average_sentiment_count"] > 3]
sdf["chat-message"] = "The sentiment of this conversation is very negative, can you increase politeness?"

sdf = sdf.apply(update_row, stateful=True)
sdf = sdf[sdf["chat-message"] != "SENT"]

sdf = sdf.update(lambda row: print(row))


sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)