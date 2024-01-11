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

app = Application.Quix("transformation-v1-side-"+os.environ["consumergroup"], auto_offset_reset="latest")

input_topic = app.topic(os.environ["input"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["input"], value_serializer=QuixTimeseriesSerializer())



role = consumergroup

def init():
    chat_id = str(uuid.uuid4()) # Give the conversation an ID for effective message keying

    cfg_builder = QuixKafkaConfigsBuilder()

    # Get the input topic name from an environment variable
    cfgs, topics, _ = cfg_builder.get_confluent_client_configs([os.environ["input"]])

    # Create the topic if it doesn't yet exist
    cfg_builder.create_topics([TopicCreationConfigs(name=topics[0])])

    # Define a serializer for adding the extra headers
    serializer = QuixTimeseriesSerializer()

    # Add the chat_id as an extra header so that we can use to partition the different conversation streams
    headers = {**serializer.extra_headers, "uuid": chat_id}

    # Define a dictionary for the message values
    value = {
        "conversation_id": chat,
        "role": role,
        "text": "Hello I am here to help!",
        "Timestamp": time.time_ns(),
    }

    # Initialize a Kafka Producer using the chat ID as the message key
    with Producer(broker_address=cfgs.pop("bootstrap.servers"), extra_config=cfgs) as producer:
        producer.produce(
            topic=topics[0],
            headers=headers,
            key=chat_id,
            value=serializer(value=value, ctx=SerializationContext(topic=topics[0], headers=headers)),
        )

# only A will init. B will listen and respond
# A will also respond. but only to B
if role == "A":
    print("Calling INIT!!!")
    init()

def reply(row: dict, state: State):

    chat_id = row['conversation_id']

    row["role"] = role,
    row["text"] = "This is a reply from " + role,
    row["conversation_id"] = chat_id,
    row["Timestamp"] = time.time_ns(),

    time.sleep(1)
    
    return row

sdf = app.dataframe(input_topic)

sdf = sdf[sdf["role"] != role]

sdf = sdf.apply(reply, stateful=True)

sdf = sdf.update(lambda row: print(row))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)