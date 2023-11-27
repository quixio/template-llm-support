import os
from quixstreams import Application, State
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
import uuid


app = Application.Quix("transformation-v1", auto_offset_reset="latest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())

cfg_builder = QuixKafkaConfigsBuilder()
cfgs, topics, _ = cfg_builder.get_confluent_client_configs([topic])
topic = topics[0]

producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)
serialize = QuixTimeseriesSerializer()

headers = {**self.serialize.extra_headers, "uuid": str(uuid.uuid4())}

value = {
    "Timestamp"
}

# Generate a UUID and then take the first 8 characters
key = str(uuid.uuid4())[:8]

producer.produce(
    headers=headers,
    topic=topic,
    key=key,
    value=serialize(
        value=row, ctx=SerializationContext(topic=self.topic, headers=headers)
    ))

print(f"Conversation {key} started.")