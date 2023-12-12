import os
import time
import redis
import streamlit as st

r = redis.Redis(
  host=os.environ["redis_host"],
  port=int(os.environ["redis_port"]),
  password=os.environ["redis_pwd"]
)

st.set_page_config(
    page_title="LLM Customer Support",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed"
)

keys = r.scan_iter() 
cols = st.columns([0.25, 0.25, 0.25, 0.25])

for col in cols:
    col = st.empty()

while True:
    for i, key in enumerate(keys):
        data = r.json().get(key)
        last = data[-1]
        mood_avg = ""
        
        if "average_sentiment" in last:
            if last["average_sentiment"] > 0:
                mood_avg = "Good"
            elif last["average_sentiment"] < 0:
                mood_avg = "Bad"
            else:
                mood_avg = "Neutral"
        else:
            mood_avg = "Unknown"

        with cols[i % 3].container():
            st.subheader("Conversation #{}".format(i + 1))
            st.text("Agent ID: 12345667 (Bob Johnston)")
            st.text("Customer ID: 12345677 (Sue Ladysmith)")
            st.text("Average Sentiment: " + mood_avg)

    time.sleep(0.5)

