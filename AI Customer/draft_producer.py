from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
import json

class DraftProducer:

    def __init__(self, topic: str):
        cfg_builder = QuixKafkaConfigsBuilder()
        cfgs, topics, _ = cfg_builder.get_confluent_client_configs([topic])
        self.topic = topics[0]

        self.producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)

    def __del__(self):
        self.producer.flush()
            
    def produce(self, row: dict, key: str):
        self.producer.produce(
                    topic=self.topic,
                    key=str(key),
                    value=json.dumps(row),
                )

    
