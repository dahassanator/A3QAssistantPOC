import pytest

from assistant.knowledge_base import KnowledgeBase


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    return KnowledgeBase(persist_dir=tmp_path_factory.mktemp("chroma"))


def test_political_term_question_retrieves_glossary_definition(kb):
    results = kb.search("what does the FEC mean by an independent expenditure?")

    top = results[0]
    assert top.category == "glossary"
    assert top.source == "glossary/independent-expenditure.md"
    assert "not coordinated" in top.text.lower()


def test_platform_howto_question_retrieves_howto_doc(kb):
    results = kb.search("how do I log a new canvassing contact?")

    top = results[0]
    assert top.category == "howto"
    assert top.source == "howto/log-canvassing-contact.md"
    assert "canvassing" in top.text.lower()


def test_flagged_source_carries_its_known_issue(kb):
    results = kb.search(
        "statement of economic interests salary threshold for ethics law", k=5
    )

    flagged = next(
        p
        for p in results
        if p.source == "ethics_law/36-25-14_filing_of_statement_of_economic_interests.md"
    )
    assert flagged.flag == "Says $75,000; real threshold is $106,000"


def test_unflagged_source_has_no_flag(kb):
    results = kb.search("what does the FEC mean by an independent expenditure?")

    assert results[0].flag is None
