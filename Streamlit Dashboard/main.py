import os
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

c1, c2, c3, c4 = st.columns([0.25, 0.25, 0.25, 0.25])