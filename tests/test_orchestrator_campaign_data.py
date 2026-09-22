import json
from unittest.mock import MagicMock

import pytest

from assistant import campaign_data
from assistant.knowledge_base import KnowledgeBase
from assistant.orchestrator import handle_question


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    return KnowledgeBase(persist_dir=tmp_path_factory.mktemp("chroma"))


def _tool_use(name, tool_input, tool_id="toolu_1"):
    block = MagicMock(type="tool_use", id=tool_id, input=tool_input)
    block.name = name
    return block


def test_data_tool_call_returns_computed_figures_not_a_citation(kb):
    tool_use = _tool_use("get_contributions", {"donor": "Pete Wallace"})
    first = MagicMock(stop_reason="tool_use", content=[tool_use])
    final = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(type="text", text="That donor gave $1,200 total.")],
    )
    client = MagicMock()
    client.messages.create.side_effect = [first, final]

    answer = handle_question(
        "how much has Pete Wallace's committee given me?",
        {"state": "Alabama", "office": "Mayor"},
        client=client,
        knowledge_base=kb,
    )

    _, second_call = client.messages.create.call_args_list
    tool_result = second_call.kwargs["messages"][-1]["content"][0]
    payload = json.loads(tool_result["content"])
    assert payload == campaign_data.get_contributions(donor="Pete Wallace")

    assert answer.citations == []


def test_combined_statute_and_data_tool_round_merges_both_results(kb):
    search_call = _tool_use(
        "search_knowledge_base",
        {"query": "contribution limit from a federal candidate committee"},
        tool_id="toolu_kb",
    )
    data_call = _tool_use(
        "get_contributions", {"donor": "Pete Wallace"}, tool_id="toolu_data"
    )
    first = MagicMock(stop_reason="tool_use", content=[search_call, data_call])
    final = MagicMock(
        stop_reason="end_turn",
        content=[MagicMock(type="text", text="Yes, that's $200 over the cap.")],
    )
    client = MagicMock()
    client.messages.create.side_effect = [first, final]

    answer = handle_question(
        "has Pete Wallace's committee given me more than the law allows?",
        {"state": "Alabama", "office": "Mayor"},
        client=client,
        knowledge_base=kb,
    )

    _, second_call = client.messages.create.call_args_list
    tool_results = second_call.kwargs["messages"][-1]["content"]
    assert {r["tool_use_id"] for r in tool_results} == {"toolu_kb", "toolu_data"}

    assert any("fcpa_statute/17-5-15.1" in c for c in answer.citations)
