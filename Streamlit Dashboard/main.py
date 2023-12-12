import os
import time
import redis
import streamlit as st

r = redis.Redis(
  host=os.environ["redis_host"],
  port=int(os.environ["redis_port"]),
  password=os.environ["redis_pwd"]
)

key_prefix = os.environ["Quix__Workspace__Id"] + ":"

st.set_page_config(
    page_title="LLM Customer Support",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed"
)

cols = st.columns([0.25, 0.25, 0.25, 0.25])

for col in cols:
    col = st.empty()

while True:
    chats = []

    for key in r.scan_iter() :
        if key.starswith(key_prefix):
            chats.append(r.json().get(key))

    for i, chat in enumerate(chats):
        last = chat[-1]
        mood_avg = ""
        
        if last["average_sentiment"] > 0:
            mood_avg = "Good"
        elif last["average_sentiment"] < 0:
            mood_avg = "Bad"
        else:
            mood_avg = "Neutral"

        with cols[i % 3].container():
            st.subheader("Conversation #{}".format(i + 1))
            st.text("Agent ID: {} ({})".format(last["agent_id"], last["agent_name"]))
            st.text("Customer ID: {} ({})".format(last["customer_id"], last["customer_name"]))
            st.text("Average Sentiment: " + mood_avg)

    time.sleep(1)

