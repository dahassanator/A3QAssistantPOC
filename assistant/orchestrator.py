"""The single orchestration entry point the Streamlit UI calls.

`handle_question` is the one seam this whole app is tested through (see
ticket #2 and the published spec's Testing Decisions). It currently just
calls Claude directly with no retrieval, tools, or safety layer - those
are wired in by later tickets (#3, #4, #5, #6) without changing this
function's signature or return shape.
"""

from dataclasses import dataclass, field

import anthropic

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT_TEMPLATE = (
    "You are an AI assistant for campaign staff using the VoteCivic/SignalVote "
    "platform. You help with campaign-finance compliance questions, political "
    "terminology, platform how-to questions, and questions about the user's own "
    "campaign. The current user is working on a campaign in {state} "
    "({office} race). Be concise and accurate."
)


@dataclass
class AssistantAnswer:
    text: str
    category: str = "general"
    citations: list[str] = field(default_factory=list)
    refused: bool = False
    redacted: bool = False


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def handle_question(
    question: str,
    campaign_context: dict,
    client: anthropic.Anthropic | None = None,
) -> AssistantAnswer:
    client = client or _get_client()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        state=campaign_context.get("state", "Alabama"),
        office=campaign_context.get("office", "Mayoral"),
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    text = next((block.text for block in response.content if block.type == "text"), "")
    return AssistantAnswer(text=text)
