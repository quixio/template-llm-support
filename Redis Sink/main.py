import quixstreams as qx
import os
import pandas as pd

client = qx.QuixStreamingClient()
topic_consumer = client.get_topic_consumer(topic_id_or_name = os.environ["input"])

def on_stream_recv_handler(sc: qx.StreamConsumer):
    def on_data_recv_handler(stream_consumer: qx.StreamConsumer, df: pd.DataFrame):
        print(df)
    
    sc.timeseries.on_dataframe_received = on_data_recv_handler

topic_consumer.on_stream_received = on_stream_recv_handler

print("Listening to streams. Press CTRL-C to exit.")
qx.App.run()