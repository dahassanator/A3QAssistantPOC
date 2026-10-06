import base64
import os
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from assistant.campaign import get_default_campaign_context
from assistant.campaign_data import (
    CANVASSING_LOG,
    CONTRIBUTIONS,
    EXPENDITURES,
    FILING_DEADLINES,
)
from assistant.orchestrator import handle_question
from assistant.statute_links import link_statutes

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ.setdefault("ANTHROPIC_API_KEY", st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    pass

st.set_page_config(page_title="A3Q AI Assistant (POC)", page_icon="🗳️", layout="wide")

# The left pane is a screenshot of the VoteCivic Finance page with its content
# area blacked out; the campaign data is laid over that blacked-out box. Box
# bounds are in screenshot pixels and are converted to percentages of the
# frame's width so the overlay tracks the image as the column resizes. The
# black box ends at x=1107, but the overlay runs to the frame's right edge to
# hide the sliver of cut-off cards between the box and the chat.
FRAME_IMAGE = Path(__file__).parent / "assets" / "votecivic_frame.png"
FRAME_W, FRAME_H = 1138, 909
BOX_LEFT, BOX_TOP, BOX_RIGHT, BOX_BOTTOM = 84, 205, FRAME_W, 908


def pct(px: int) -> str:
    return f"{px / FRAME_W * 100:.4f}%"


@st.cache_data
def frame_data_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(FRAME_IMAGE.read_bytes()).decode()


# st.html with only <style> content goes to Streamlit's event container, so
# it doesn't take up a row (and a flex gap) at the top of the page.
st.html(
    f"""
<style>
header[data-testid="stHeader"] {{ display: none; }}
.block-container {{ padding: 0 1rem 0 0; max-width: none; }}
.st-key-platform_frame {{
    background: url("{frame_data_uri()}") top left / 100% auto no-repeat;
    aspect-ratio: {FRAME_W} / {FRAME_H};
    padding: {pct(BOX_TOP)} {pct(FRAME_W - BOX_RIGHT)} 0 {pct(BOX_LEFT)};
}}
.st-key-campaign_panel {{
    aspect-ratio: {BOX_RIGHT - BOX_LEFT} / {BOX_BOTTOM - BOX_TOP};
    overflow-y: auto;
    background: #fff;
    padding: 0.5rem 1rem 1rem;
    /* Covers sub-pixel slivers of the screenshot's black box at the edges. */
    box-shadow: 0 0 0 2px #fff;
}}
.st-key-chat_pane {{ padding-top: 1rem; }}
.st-key-chat_history,
[data-testid="stLayoutWrapper"]:has(> .st-key-chat_history) {{
    height: calc(100vh - 6.5rem) !important;
    flex-basis: calc(100vh - 6.5rem) !important;
}}
</style>
"""
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


data_col, chat_col = st.columns([13, 7], gap="medium")

with data_col:
    with st.container(key="platform_frame"):
        with st.container(key="campaign_panel"):
            render_campaign_data()

with chat_col, st.container(key="chat_pane"):
    if "messages" not in st.session_state:
        st.session_state.messages = []

    history = st.container(height=PANEL_HEIGHT, key="chat_history")
    with history:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                # Assistant answers are stored already linked and HTML-escaped
                # (see link_statutes); user messages never get HTML rendering.
                st.markdown(
                    msg["content"], unsafe_allow_html=msg["role"] == "assistant"
                )

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
                displayed_answer = link_statutes(answer.text.replace("$", "\\$"))
                st.markdown(displayed_answer, unsafe_allow_html=True)

        st.session_state.messages.append(
            {"role": "assistant", "content": displayed_answer}
        )
