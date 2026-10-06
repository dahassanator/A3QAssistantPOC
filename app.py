import os
from dataclasses import asdict

import streamlit as st

from assistant.campaign import get_default_campaign_context
from assistant.campaign_data import (
    CANVASSING_LOG,
    CONTRIBUTIONS,
    EXPENDITURES,
    FILING_DEADLINES,
)
from assistant.orchestrator import handle_question

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ.setdefault("ANTHROPIC_API_KEY", st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    pass

st.set_page_config(page_title="A3Q AI Assistant (POC)", page_icon="🗳️", layout="wide")
st.title("A3Q AI Assistant — POC")
st.caption(
    "Demo scope: Alabama compliance, platform how-tos, political terminology, "
    "and one fictional campaign's data."
)

campaign = get_default_campaign_context()
PANEL_HEIGHT = 560
money = st.column_config.NumberColumn(format="$%.2f")


def render_campaign_data() -> None:
    st.subheader(campaign["campaign_name"])
    st.caption(
        f"{campaign['candidate_name']} · {campaign['office']} of {campaign['town']} · "
        f"Election {campaign['election_date']} · Data as of {campaign['as_of_date']}"
    )

    contributions, expenditures, canvassing, deadlines = st.tabs(
        ["Contributions", "Expenditures", "Canvassing Log", "Filing Deadlines"]
    )

    with contributions:
        st.metric("Total raised", f"${sum(c.amount for c in CONTRIBUTIONS):,.2f}")
        st.dataframe(
            [asdict(c) for c in CONTRIBUTIONS],
            column_config={"amount": money},
            hide_index=True,
            width="stretch",
        )

    with expenditures:
        st.metric("Total spent", f"${sum(e.amount for e in EXPENDITURES):,.2f}")
        st.dataframe(
            [asdict(e) for e in EXPENDITURES],
            column_config={"amount": money},
            hide_index=True,
            width="stretch",
        )

    with canvassing:
        attempted, reached, supporters = st.columns(3)
        attempted.metric("Attempted", sum(c.contacts_attempted for c in CANVASSING_LOG))
        reached.metric("Reached", sum(c.contacts_reached for c in CANVASSING_LOG))
        supporters.metric(
            "Supporters", sum(c.supporters_identified for c in CANVASSING_LOG)
        )
        st.dataframe(
            [asdict(c) for c in CANVASSING_LOG],
            hide_index=True,
            width="stretch",
        )

    with deadlines:
        st.dataframe(
            [asdict(d) for d in FILING_DEADLINES],
            hide_index=True,
            width="stretch",
            height=PANEL_HEIGHT - 100,
        )


data_col, chat_col = st.columns([2, 3], gap="large")

with data_col:
    render_campaign_data()

with chat_col:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    history = st.container(height=PANEL_HEIGHT)
    with history:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    question = st.chat_input("Ask a compliance, how-to, or terminology question...")

    if question:
        # Streamlit's markdown renderer treats single `$...$` as inline LaTeX math,
        # which garbles dollar-amount citations (e.g. "$100 ... $5,000") into
        # broken math blocks. Escape before display only - the backend safety
        # checks (PII redaction, injection detection) run on the raw question.
        displayed_question = question.replace("$", "\\$")
        st.session_state.messages.append({"role": "user", "content": displayed_question})
        with history:
            with st.chat_message("user"):
                st.markdown(displayed_question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = handle_question(question, campaign)
                displayed_answer = answer.text.replace("$", "\\$")
                st.markdown(displayed_answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": displayed_answer}
        )
