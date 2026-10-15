"""Guards the hard eval set against invented statute content: every quoted
source must appear verbatim in its knowledge-base file, at the line cited."""

import pytest

from assistant.knowledge_base import DEFAULT_DOCS_DIR
from eval.eval_questions import QUESTIONS
from eval.eval_questions_hard import QUESTIONS_HARD

SOURCES = [(q.id, s) for q in QUESTIONS_HARD for s in q.sources]


@pytest.mark.parametrize("question_id,source", SOURCES, ids=[f"{q}:{s.path}:{s.line}" for q, s in SOURCES])
def test_quote_is_verbatim_at_cited_line(question_id, source):
    text = (DEFAULT_DOCS_DIR / source.path).read_text()
    assert source.quote in text
    lines = text.splitlines()
    first_quote_line = source.quote.splitlines()[0]
    assert first_quote_line in lines[source.line - 1]


def test_every_hard_question_is_marked_for_review_and_sourced():
    for q in QUESTIONS_HARD:
        assert q.needs_human_review
        assert q.sources
        assert q.question_types


def test_ids_do_not_collide_with_original_set():
    ids = [q.id for q in QUESTIONS] + [q.id for q in QUESTIONS_HARD]
    assert len(ids) == len(set(ids))
