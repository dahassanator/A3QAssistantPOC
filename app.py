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
    # Streamlit's markdown renderer treats single `$...$` as inline LaTeX math,
    # which garbles dollar-amount citations (e.g. "$100 ... $5,000") into
    # broken math blocks. Escape before display only - the backend safety
    # checks (PII redaction, injection detection) run on the raw question.
    displayed_question = question.replace("$", "\\$")
    st.session_state.messages.append({"role": "user", "content": displayed_question})
    with st.chat_message("user"):
        st.markdown(displayed_question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = handle_question(question, get_default_campaign_context())
        displayed_answer = answer.text.replace("$", "\\$")
        st.markdown(displayed_answer)

    st.session_state.messages.append({"role": "assistant", "content": displayed_answer})
