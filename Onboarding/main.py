import os
from quixstreams import Application, State


app = Application.Quix("transformation-v1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer='json')

sdf = app.dataframe(input_topic)

# Here put transformation logic.

sdf = sdf.update(lambda row: print(row))


if __name__ == "__main__":
    app.run(sdf)