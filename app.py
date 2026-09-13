import os

import streamlit as st

from assistant.campaign import get_default_campaign_context
from assistant.orchestrator import handle_question

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ.setdefault("ANTHROPIC_API_KEY", st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    pass

st.set_page_config(page_title="A3Q AI Assistant (POC)", page_icon="🗳️")
st.title("A3Q AI Assistant — POC")
st.caption(
    "Demo scope: Alabama compliance, platform how-tos, political terminology, "
    "and one fictional campaign's data."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("Ask a compliance, how-to, or terminology question..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = handle_question(question, get_default_campaign_context())
        st.markdown(answer.text)

    st.session_state.messages.append({"role": "assistant", "content": answer.text})
