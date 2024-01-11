import os
import time
import uuid
import random
import re
from pathlib import Path
import pickle
import glob

from quixstreams import Application, State
from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder, TopicCreationConfigs
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer, SerializationContext

consumergroup = os.environ["consumergroup"]
role = os.environ["role"]

app = Application.Quix(f"transformation-{os.environ['consumergroup']}-{os.environ['role']}", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["input"], value_serializer=QuixTimeseriesSerializer())

sdf = app.dataframe(input_topic)

sdf = sdf.update(lambda row: print(row))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)