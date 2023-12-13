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

maxlen = 12
containers = []
cols = st.columns([0.25, 0.25, 0.25, 0.25])

for i in range(maxlen):
    with cols[i % 3]:
        containers.append((st.empty(), st.empty()))

while True:
    count = 0
    chats = []

    for key in r.scan_iter() :
        if key.decode().startswith(key_prefix):
            chat = r.json().get(key)
            # customer_id is not available until the customer responds to agent
            if chat and "customer_id" in chat[-1]:
                chats.append(chat)
                count += 1
                # limit the number of chats displayed
                if count >= maxlen:
                    break

    for i, c in enumerate(containers):
        c[0].empty()
        c[1].empty()

        if i < len(chats):
            msg_latest = chats[i][-1]
            mood_avg = ""
            if msg_latest["average_sentiment"] > 0:
                mood_avg = "Good"
            elif msg_latest["average_sentiment"] < 0:
                mood_avg = "Bad"
            else:
                mood_avg = "Neutral"

            with c[0].container():
                st.subheader(f"Conversation #{i + 1}")
                st.text(f"Agent ID: {msg_latest['agent_id']:.0f} ({msg_latest['agent_name']})")
                st.text(f"Customer ID: {msg_latest['customer_id']:.0f} ({msg_latest['customer_name']})")
                st.text("Average Sentiment: " + mood_avg)
            
            with c[1].container(border=True):
                for msg in chats[i]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["text"])

    time.sleep(1)

