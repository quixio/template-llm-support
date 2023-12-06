import quixstreams as qx
import os
import pandas as pd


token_env_var = "external_token"
input_topic_env_var = "input"
output_topic_env_var = "output"
external_env_token = os.getenv(token_env_var)
input_topic = os.getenv(input_topic_env_var)
output_topic = os.getenv(output_topic_env_var)

if external_env_token is None:
    print(f"The environment variable {token_env_var} is not set.")
    raise Exception(f"The environment variable {token_env_var} is not set.")

if output_topic is None:
    print(f"The environment variable {output_topic_env_var} is not set.")
    raise Exception(f"The environment variable {output_topic_env_var} is not set.")

if input_topic is None:
    print(f"The environment variable {input_topic_env_var} is not set.")
    raise Exception(f"The environment variable {input_topic_env_var} is not set.")


# Quix injects credentials automatically to the client. 
# Alternatively, you can always pass an SDK token manually as an argument.
external_quix_client = qx.QuixStreamingClient(token=external_env_token)
# no token needed as this will use the token from your workspace when deployed in Quix
internal_quix_client = qx.QuixStreamingClient()

# setup to consume from the external Quix topic (external is the one OUTside of this project or repo)
topic_consumer = external_quix_client.get_topic_consumer(input_topic, consumer_group = "quix-quix-connector")

# and produce to the internal Quix topic (internal is the one INside of this project or repo)
topic_producer = internal_quix_client.get_topic_producer(output_topic)


def on_stream_received_handler(stream_consumer: qx.StreamConsumer):

    def on_dataframe_received_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
        stream_producer = topic_producer.get_or_create_stream(stream_id = stream_consumer.stream_id)
        stream_producer.timeseries.buffer.publish(df)

    # Handle event data from samples that emit event data
    def on_event_data_received_handler(stream_consumer: qx.StreamConsumer, data: qx.EventData):
        print(data)
        # handle your event data here

    stream_consumer.events.on_data_received = on_event_data_received_handler # register the event data callback
    stream_consumer.timeseries.on_dataframe_received = on_dataframe_received_handler


# subscribe to new streams being received
topic_consumer.on_stream_received = on_stream_received_handler

print("Listening to streams. Press CTRL-C to exit.")

# Handle termination signals and provide a graceful exit
qx.App.run()
