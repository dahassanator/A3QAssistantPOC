"""Repeatable eval runner (ticket #7).

Runs every question in eval_questions.QUESTIONS against the real
orchestrator (a live Claude call, same code path as the deployed app),
grades each answer against its rubric, prints a summary, and writes a
timestamped JSON record under eval/results/.

Usage:
    ANTHROPIC_API_KEY=... python -m eval.run_eval
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from assistant.campaign import get_default_campaign_context
from assistant.orchestrator import handle_question
from eval.eval_questions import QUESTIONS

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def grade(question, answer) -> dict:
    checks = {}

    if question.expect_refused is not None:
        checks["refused"] = answer.refused == question.expect_refused

    if question.expect_answer_category is not None:
        checks["answer_category"] = answer.category == question.expect_answer_category

    if question.expect_citation_contains:
        checks["citations"] = all(
            any(sub in citation for citation in answer.citations)
            for sub in question.expect_citation_contains
        )

    if question.expect_text_contains_all:
        text = answer.text.lower()
        checks["text_contains_all"] = all(
            kw.lower() in text for kw in question.expect_text_contains_all
        )

    if question.expect_text_contains_any:
        text = answer.text.lower()
        checks["text_contains_any"] = any(
            kw.lower() in text for kw in question.expect_text_contains_any
        )

    if question.expect_text_not_contains:
        text = answer.text.lower()
        checks["text_not_contains"] = not any(
            kw.lower() in text for kw in question.expect_text_not_contains
        )

    return {"checks": checks, "passed": all(checks.values())}


def run() -> list[dict]:
    ctx = get_default_campaign_context()
    results = []

    for q in QUESTIONS:
        answer = handle_question(q.question, ctx)
        outcome = grade(q, answer)
        results.append(
            {
                "id": q.id,
                "eval_category": q.eval_category,
                "question": q.question,
                "passed": outcome["passed"],
                "checks": outcome["checks"],
                "answer_category": answer.category,
                "refused": answer.refused,
                "citations": answer.citations,
                "answer_text": answer.text,
            }
        )
        status = "PASS" if outcome["passed"] else "FAIL"
        print(f"[{status}] {q.id} ({q.eval_category})")
        if not outcome["passed"]:
            failed_checks = [k for k, v in outcome["checks"].items() if not v]
            print(f"       failed checks: {failed_checks}")
            print(f"       answer: {answer.text[:200]!r}")

    return results


def summarize(results: list[dict]) -> None:
    total = len(results)
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{total} passed overall\n")

    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["eval_category"], []).append(r)

    for category, rows in sorted(by_category.items()):
        cat_passed = sum(r["passed"] for r in rows)
        print(f"  {category}: {cat_passed}/{len(rows)}")


def main() -> int:
    results = run()
    summarize(results)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out_path.relative_to(Path.cwd())}")

    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
