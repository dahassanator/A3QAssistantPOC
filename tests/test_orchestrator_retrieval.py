from unittest.mock import MagicMock

import pytest

from assistant.knowledge_base import KnowledgeBase
from assistant.orchestrator import handle_question


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    return KnowledgeBase(persist_dir=tmp_path_factory.mktemp("chroma"))


def _scripted_client(search_query: str, final_text: str):
    search_call = MagicMock(type="tool_use", id="toolu_1", input={"query": search_query})
    search_call.name = "search_knowledge_base"
    first = MagicMock(stop_reason="tool_use", content=[search_call])

    answer_call = MagicMock(type="tool_use", id="toolu_2", input={"text": final_text})
    answer_call.name = "provide_answer"
    final = MagicMock(stop_reason="tool_use", content=[answer_call])

    client = MagicMock()
    client.messages.create.side_effect = [first, final]
    return client


def test_claude_searches_knowledge_base_and_answer_cites_source(kb):
    client = _scripted_client(
        "FEC independent expenditure definition", "It is spending not coordinated."
    )

    answer = handle_question(
        "what does the FEC mean by an independent expenditure?",
        {"state": "Alabama", "office": "Mayoral"},
        client=client,
        knowledge_base=kb,
    )

    first_call, second_call = client.messages.create.call_args_list
    assert "search_knowledge_base" in [t["name"] for t in first_call.kwargs["tools"]]

    tool_result = second_call.kwargs["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_1"
    assert "not made in cooperation" in tool_result["content"]

    assert answer.text == "It is spending not coordinated."
    assert "glossary/independent-expenditure.md" in answer.citations
