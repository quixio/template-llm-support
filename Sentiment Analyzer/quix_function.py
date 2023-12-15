import quixstreams as qx
from transformers import Pipeline
import pandas as pd


class QuixFunction:
    def __init__(self, consumer_stream: qx.StreamConsumer, producer_stream: qx.StreamProducer, classifier: Pipeline):
        self.consumer_stream = consumer_stream
        self.producer_stream = producer_stream
        self.classifier = classifier

        self.sum = 0
        self.count = 0

    def on_dataframe_handler(self, consumer_stream: qx.StreamConsumer, df_all_messages: pd.DataFrame):
        try:
            model_response = self.classifier(list(df_all_messages["text"]))
            df = pd.concat([df_all_messages, pd.DataFrame(model_response)], axis = 1)

            for i, row in df.iterrows():
                df.loc[i, "sentiment"] = 1 if row["label"] == "POSITIVE" else -1
                self.count = self.count + 1
                self.sum = self.sum + df.loc[i, "sentiment"]
                df.loc[i, "average_sentiment"] = float(self.sum) / self.count

            print(df)
            self.producer_stream.timeseries.publish(df)

        except Exception as e:
            print("Skipping frame", e)
