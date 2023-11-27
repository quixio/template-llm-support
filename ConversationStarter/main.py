import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from quixstreams.models.serializers import (
    QuixTimeseriesSerializer,
    SerializationContext,
)
from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
import uuid
import time

app = Application.Quix("transformation-v1", auto_offset_reset="latest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

cfg_builder = QuixKafkaConfigsBuilder()
cfgs, topics, _ = cfg_builder.get_confluent_client_configs([topic])
topic = topics[0]

producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)
serialize = QuixTimeseriesSerializer()

headers = {**serialize.extra_headers, "uuid": str(uuid.uuid4())}

# Generate a UUID and then take the first 8 characters
key = str(uuid.uuid4())[:8]

row = {
  "Timestamps": [
    time.time_ns()
  ],
  "NumericValues": {},
  "StringValues": {
    "chat-message": [
      " Thank you so much for sharing your experience with us, {customer}. I can understand why it would be frustrating when dealing with customer support representatives who are not helpful or knowledgeable about the product they're supporting. Unfortunately, we have had issues in the past where our representatives may not always have all the necessary information to address a problem right away, but please know that their priority is still"
    ]
  },
  "TagValues": {
    "room": [
      key
    ],
    "role": [
      "agent"
    ],
    "name": [
      "agent"
    ],
  }
}


producer.produce(
    headers=headers,
    topic=topic,
    key=key,
    value=serialize(
        value=row, ctx=SerializationContext(topic=topic, headers=headers)
    ))

print(f"Conversation {key} started.")