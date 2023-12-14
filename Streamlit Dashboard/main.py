import os
import time
import redis
import pandas as pd
import altair as alt
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
    initial_sidebar_state="collapsed",
    menu_items=None
)

# apply custom css
with open(os.environ["style_sheet"]) as f:
    st.markdown('<style>{}</style>'.format(f.read()), unsafe_allow_html=True)

maxlen = int(os.environ["chat_count"])
containers = []
cols = st.columns([0.25, 0.25, 0.25, 0.25])

with cols[3]:
    chart_title = st.empty()
    chart = st.empty()

for i in range(maxlen):
    with cols[i % 3]:
        containers.append((st.empty(), st.empty()))

def get_column_name(i: int):
    return f"Conversation #{i + 1}"

alt_x = alt.X("index", axis=None)
alt_y = alt.Y("sentiment", axis=None)
alt_legend = alt.Legend(title=None, orient="bottom", direction="vertical")
alt_color = alt.Color("conversation", legend=alt_legend)

while True:
    count = 0
    chats = []
    sentiment_data = {}

    for key in r.scan_iter() :
        if key.decode().startswith(key_prefix):
            chat = r.json().get(key)
            # customer_id is not available until the customer responds to agent
            if chat and "customer_name" in chat[-1] and chat[-1]["customer_name"]:
                chats.append(chat)
                sentiment_data[get_column_name(count)] = []
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

            col_name = get_column_name(i)
            for msg in chats[i]:
                sentiment_data[col_name].append(msg["sentiment"])                

    with chart_title.container():
        st.subheader("Customer Success Team")
        st.text("SENTIMENT DASHBOARD")
        st.markdown("#")
        st.text("Sentiment History")

    with chart.container(border=True):
        chart_data = pd.DataFrame.from_dict(sentiment_data, orient="index").T
        chart_data = chart_data.melt(var_name="conversation", value_name="sentiment")
        chart_data = chart_data.reset_index()

        alt_chart = alt.Chart(chart_data) \
                .mark_line() \
                .encode(x=alt_x, y=alt_y, color=alt_color) \

        st.altair_chart(alt_chart, use_container_width=True)

    time.sleep(1)

