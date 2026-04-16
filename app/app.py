import streamlit as st

st.set_page_config(
    page_title="FAQ Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from chat_page import render as chat_render  # noqa: E402
from files_page import render as files_render  # noqa: E402

tab_chat, tab_files = st.tabs(["💬 Chat", "📁 Files"])

with tab_chat:
    chat_render()

with tab_files:
    files_render()
