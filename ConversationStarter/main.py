import os
from quixstreams.models.serializers import (
    QuixTimeseriesSerializer,
    SerializationContext,
)
from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
import uuid
import time


cfg_builder = QuixKafkaConfigsBuilder()
cfgs, topics, _ = cfg_builder.get_confluent_client_configs([os.environ["output"]])
topic = topics[0]

producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)
serialize = QuixTimeseriesSerializer()

headers = {**serialize.extra_headers, "uuid": str(uuid.uuid4())}

# Generate a UUID and then take the first 8 characters
key = str(uuid.uuid4())[:8]

row = {
  "Timestamp": 
    time.time_ns()
  ,
  "chat-message":
      "Hello, welcome to ACME Electronics support, my name is Percy. How can I help you today?",
  "TagValues": {
    "room": 
      key
    ,
    "role": 
      "agent"
    ,
    "name": 
      "agent"
    ,
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