import os
import time
import redis
import pandas as pd
import altair as alt
import streamlit as st

# redis connection
r = redis.Redis(
  host=os.environ["redis_host"],
  port=int(os.environ["redis_port"]),
  password=os.environ["redis_pwd"]
)
# r.flushdb()
# redis keys for conversations are namespaced using project id to avoid collisions
# between conversations from different projects
key_prefix = os.environ["Quix__Workspace__Id"] + ":"

st.set_page_config(
    page_title="LLM Customer Support",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# apply custom css (optional)
with open(os.environ["style_sheet"]) as f:
    st.markdown('<style>{}</style>'.format(f.read()), unsafe_allow_html=True)

maxlen = int(os.environ["chat_count"])
containers = []
cols = st.columns([0.25, 0.25, 0.25, 0.25])

with cols[3]:
    chart_title = st.empty()
    chart = st.empty()

# two containers per conversation: one for the titles and stats, and the other for the messages
for i in range(maxlen):
    with cols[i % 3]:
        containers.append((st.empty(), st.empty()))

def get_chat_name(i: int):
    return f"Conversation #{i + 1}"

# customize Altair chart
alt_x = alt.X("timestamp", axis=None)
alt_y = alt.Y("sentiment", axis=None)
alt_legend = alt.Legend(title=None, orient="bottom", direction="vertical")
alt_color = alt.Color("conversation", legend=alt_legend)

# emoji based on the sentiment
def get_emoji(sentiment: float):
    if sentiment > 0:
        return "😀"
    if sentiment < 0:
        return "😡"
    return "😐"

def get_customer_info(msg):
    # first message sent by the support agent does not have customer information
    if "customer_id" in msg:
        return f"{msg['customer_id']:.0f} ({msg['customer_name']}"
    return ""

# main loop to poll redis for conversation updates and update the dashboard
while True:
    count = 0
    chats = []
    sentiment_data = {}

    # fetch keys for conversations from the current project from redis
    for key in r.scan_iter(key_prefix + "*") :
        chat = r.json().get(key)
        if chat:
            chats.append(chat)
            sentiment_data["timestamp"] = []
            sentiment_data["sentiment"] = []
            sentiment_data["conversation"] = []
            count += 1
            # limit the number of chats displayed
            if count >= maxlen:
                break
    
    for i, c in enumerate(containers):
        # clear old contents from containers
        c[0].empty()
        c[1].empty()

        if i < len(chats):
            msg_latest = chats[i][-1]
            mood_avg = ""
            if msg_latest["average_sentiment"] > 0:
                mood_avg = f"**:green[Good ({msg_latest['average_sentiment']:.2f})]**"
            elif msg_latest["average_sentiment"] < 0:
                mood_avg = f"**:red[Bad ({msg_latest['average_sentiment']:.2f})]**"
            else:
                mood_avg = f"**:orange[Neutral ({msg_latest['average_sentiment']:.2f})]**"

            # chat title and sentiment stats
            with c[0].container():
                st.subheader(f"Conversation #{i + 1}")
                st.markdown(f"**Agent ID:** {msg_latest['agent_id']:.0f} ({msg_latest['agent_name']})")
                st.markdown(f"**Customer ID:** {get_customer_info(msg_latest)})")
                st.markdown(f"**Average Sentiment:** {mood_avg}")
            
            with c[1].container(border=True):
                for msg in chats[i]:
                    with st.chat_message("human" if msg["role"] == "customer" else "assistant"):
                        # a bit of custom html and css to align the sentiment nicely
                        st.markdown(f"{msg['text']} <div style='text-align: right'>{get_emoji(msg['sentiment'])}</div>", unsafe_allow_html=True)

            chat_name = get_chat_name(i)
            for msg in chats[i]:
                sentiment_data["timestamp"].append(msg["timestamp"])                
                sentiment_data["sentiment"].append(msg["sentiment"])
                sentiment_data["conversation"].append(get_chat_name(i))                

    # sentiment dashboard
    if "timestamp" in sentiment_data and len(sentiment_data["timestamp"]) > 0:
        with chart_title.container():
            st.subheader("Customer Success Team")
            st.markdown("SENTIMENT DASHBOARD")
            st.markdown("#")
            st.markdown("Sentiment History")

        with chart.container(border=True):
            chart_data = pd.DataFrame.from_dict(sentiment_data, orient="index").T
            chart_data.sort_values("timestamp", inplace=True)
            alt_chart = alt.Chart(chart_data) \
                    .mark_line(interpolate='step-after') \
                    .encode(x=alt_x, y=alt_y, color=alt_color) \

            st.altair_chart(alt_chart, use_container_width=True)

    time.sleep(1)

