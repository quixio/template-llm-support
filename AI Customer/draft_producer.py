from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
from quixstreams.models.serializers import (
    QuixTimeseriesSerializer,
    SerializationContext,
)
import uuid

class DraftProducer:

    def __init__(self, topic: str):
        cfg_builder = QuixKafkaConfigsBuilder()
        cfgs, topics, _ = cfg_builder.get_confluent_client_configs([topic])
        self.topic = topics[0]

        self.producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)
        self.serialize = QuixTimeseriesSerializer()

    def __del__(self):
        self.producer.flush()
            
    def produce(self, row: dict, key: str):

        headers = {**self.serialize.extra_headers, "uuid": str(uuid.uuid4())}

        self.producer.produce(
            headers=headers,
            topic=self.topic,
            key=str(key),
            value=self.serialize(
                value=row, ctx=SerializationContext(topic=self.topic, headers=headers)
            ))

    
