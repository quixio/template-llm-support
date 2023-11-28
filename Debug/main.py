import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
import time

app = Application.Quix("transformation-v2", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
#output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)

# Here put transformation logic.

sdf = sdf.update(lambda row: print(row["Timestamp"]))
sdf["Timestamp"] = time.time_ns()
sdf = sdf.update(lambda row: print(row["Timestamp"]))

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)