from quixstreams.kafka import Producer
from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
import os
import random
import pandas as pd
import json
from datetime import datetime, timedelta


def main():


    cfg_builder = QuixKafkaConfigsBuilder()
    cfgs, topics, _ = cfg_builder.get_confluent_client_configs([os.environ["output"]])
    topic = topics[0]

    with Producer(
        cfgs.pop("bootstrap.servers"), extra_config=cfgs
    ) as producer:
        
        # Creating a sample DataFrame

        # Sample data parameters
        num_samples = 10  # Number of samples to generate
        user_ids = [1001, 1002, 1003, 1004, 1005]  # Example user IDs
        impressions = ['click', 'view', 'interact']  # Example impression types

        # Generate sample data
        data = {
            'Timestamp': [datetime.now() - timedelta(days=random.randint(0, 30)) for _ in range(num_samples)],
            'user_id': [random.choice(user_ids) for _ in range(num_samples)],
            'impression': [random.choice(impressions) for _ in range(num_samples)]
        }

        # Create DataFrame
        df = pd.DataFrame(data)

        df['Timestamp'] = df['Timestamp'].apply(lambda x: x.strftime('%Y-%m-%dT%H:%M:%S'))


        # Displaying the first few rows of the DataFrame
        print(df)

        for index, row in df.iterrows():

            print(row.to_dict())
 
            producer.produce(
                topic=topic,
                key=str(row["user_id"]),
                value=json.dumps(row.to_dict()),
            )




if __name__ == "__main__":
    main()



