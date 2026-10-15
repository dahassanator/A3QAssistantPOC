from unittest.mock import MagicMock

import pytest

from assistant.knowledge_base import KnowledgeBase
from assistant.orchestrator import ALL_TOOLS, handle_question
from assistant.retrieval_strategies import (
    citations_from_text,
    reciprocal_rank_fusion,
    search_text,
)

SEI_STATUTE = "ethics_law/36-25-14_filing_of_statement_of_economic_interests.md"
CONTEXT = {"state": "Alabama", "office": "Mayoral"}


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    return KnowledgeBase(persist_dir=tmp_path_factory.mktemp("chroma"))


def _tool_call(name, tool_input, call_id):
    block = MagicMock(type="tool_use", id=call_id, input=tool_input)
    block.name = name
    return block


def _scripted_client(*rounds):
    client = MagicMock()
    client.messages.create.side_effect = [MagicMock(content=list(r)) for r in rounds]
    return client


def _answer(text, call_id="toolu_final"):
    return [_tool_call("provide_answer", {"text": text}, call_id)]


def _tool_names(call):
    return [t["name"] for t in call.kwargs["tools"]]


def test_default_strategy_is_rag_current(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_STRATEGY", raising=False)
    client = _scripted_client(_answer("Hi."))

    handle_question("hello", CONTEXT, client=client)

    assert client.messages.create.call_args.kwargs["tools"] == ALL_TOOLS


def test_env_var_selects_strategy(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_STRATEGY", "agentic_nav")
    client = _scripted_client(_answer("Hi."))

    handle_question("hello", CONTEXT, client=client)

    assert "read_document" in _tool_names(client.messages.create.call_args)


def test_unknown_strategy_is_rejected():
    with pytest.raises(ValueError, match="Unknown retrieval strategy"):
        handle_question("hello", CONTEXT, client=MagicMock(), strategy="nope")


def test_long_context_caches_whole_kb_and_cites_sections_it_names():
    client = _scripted_client(_answer("Under § 36-25-14 the threshold is $106,000."))

    answer = handle_question(
        "SEI threshold?", CONTEXT, client=client, strategy="long_context"
    )

    call = client.messages.create.call_args
    kb_block, instructions = call.kwargs["system"]
    assert kb_block["cache_control"] == {"type": "ephemeral"}
    assert f"[{SEI_STATUTE}]\nKnown issue: Says $75,000" in kb_block["text"]
    assert "search_knowledge_base" not in instructions["text"]
    assert "search_knowledge_base" not in _tool_names(call)
    assert answer.citations == [SEI_STATUTE]


def test_agentic_nav_cites_only_documents_it_read_with_their_flags():
    client = _scripted_client(
        [_tool_call("search_text", {"query": "106,000"}, "t1")],
        [_tool_call("read_document", {"path": SEI_STATUTE}, "t2")],
        _answer("It is $106,000 (§ 36-25-14)."),
    )

    answer = handle_question(
        "SEI threshold?", CONTEXT, client=client, strategy="agentic_nav"
    )

    read_result = client.messages.create.call_args.kwargs["messages"][-1]["content"][0]
    assert "Known issue: Says $75,000" in read_result["content"]
    assert answer.citations == [SEI_STATUTE]


def test_agentic_nav_refuses_paths_outside_the_corpus():
    client = _scripted_client(
        [_tool_call("read_document", {"path": "../.streamlit/secrets.toml"}, "t1")],
        _answer("Done."),
    )

    answer = handle_question("x", CONTEXT, client=client, strategy="agentic_nav")

    result = client.messages.create.call_args.kwargs["messages"][-1]["content"][0]
    assert result["content"].startswith("No document at")
    assert answer.citations == []


def test_agentic_nav_10_gets_ten_rounds():
    rounds = [[_tool_call("list_categories", {}, f"t{i}")] for i in range(10)]
    client = _scripted_client(*rounds, _answer("Done."))

    handle_question("x", CONTEXT, client=client, strategy="agentic_nav_10")

    assert client.messages.create.call_count == 11
    assert _tool_names(client.messages.create.call_args) == [
        "decline_to_answer",
        "provide_answer",
    ]


def test_search_text_falls_back_to_literal_on_bad_regex():
    assert "17-5-8(a" in search_text("17-5-8(a").replace("§", "")


def test_rrf_rewards_items_ranked_by_both_lists():
    assert reciprocal_rank_fusion([["a", "b", "c"], ["c", "d"]])[0] == "c"


def test_citations_from_text_maps_sections_and_opinions():
    found = citations_from_text("See § 17-5-15.1(a) and AG Op. 94-00227.")
    assert found == [
        "fcpa_statute/17-5-15.1_limit_on_federal_funds_in_state_races.md",
        "ag_opinions/AGO_94-00227_paid_advertisement_wording_and_identification.md",
    ]


def test_hybrid_finds_section_named_by_number(kb):
    client = _scripted_client(
        [_tool_call("search_knowledge_base", {"query": "17-5-15.1 cap"}, "t1")],
        _answer("Done."),
    )

    answer = handle_question(
        "x", CONTEXT, client=client, knowledge_base=kb, strategy="hybrid"
    )

    assert len(answer.citations) == 3
    assert answer.citations[0].startswith("fcpa_statute/17-5-15.1_")


def test_glossary_inline_moves_glossary_from_search_to_prompt(kb):
    client = _scripted_client(
        [_tool_call("search_knowledge_base", {"query": "what is a PAC"}, "t1")],
        _answer("A political action committee (glossary/pac.md)."),
    )

    answer = handle_question(
        "What is a PAC?", CONTEXT, client=client, knowledge_base=kb,
        strategy="glossary_inline",
    )

    call = client.messages.create.call_args
    assert "[glossary/pac.md]" in call.kwargs["system"]
    result = call.kwargs["messages"][-1]["content"][0]["content"]
    assert "[glossary/" not in result
    assert "glossary/pac.md" in answer.citations
