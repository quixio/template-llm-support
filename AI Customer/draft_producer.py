

def class DraftProducer:

    def __init__(self):
         cfg_builder = QuixKafkaConfigsBuilder()
        cfgs, topics, _ = cfg_builder.get_confluent_client_configs([os.environ["output"]])
        topic = topics[0]

        self.producer = Producer(cfgs.pop("bootstrap.servers"), extra_config=cfgs)

    def __del__(self):
        # Ensure the file is closed when the object is destroyed
        self.producer.
            
    def produce(row: dict):
        self.producer.produce(
                    topic=topic,
                    key=str(row["user_id"]),
                    value=json.dumps(row.to_dict()),
                )

    
