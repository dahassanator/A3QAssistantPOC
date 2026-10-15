"""Run every retrieval strategy against the original and hard eval sets.

Each (strategy, question) pair runs N times through the real
`handle_question` seam on the real model. A recording wrapper around the
Anthropic client captures per-call usage, latency and tool traffic without
touching the orchestrator, so the default code path is exactly what ships.

Usage:
    python -m experiments.run_strategy_comparison --dry-run   # 2 questions/strategy + cost estimate
    python -m experiments.run_strategy_comparison             # full run (N=3)

Results: experiments/results/<UTC timestamp>.json, plus a markdown summary
on stdout.
"""

# --- PRICING (USD per million tokens) - update here, nowhere else ---------
# Source: Anthropic pricing for claude-haiku-4-5 as of 2026-10-06. Cache
# writes are the 5-minute TTL rate (1.25x input); reads are 0.1x input.
PRICING = {
    "claude-haiku-4-5": {
        "input": 1.00,
        "output": 5.00,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
}
# --------------------------------------------------------------------------

import argparse
import json
import re
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from assistant.campaign import get_default_campaign_context
from assistant.knowledge_base import KnowledgeBase
from assistant.orchestrator import MODEL, handle_question
from assistant.retrieval_strategies import STRATEGY_NAMES, build_strategy
from eval.eval_questions import QUESTIONS
from eval.eval_questions_hard import QUESTIONS_HARD
from eval.run_eval import grade

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DRY_RUN_QUESTION_IDS = ["compliance-reporting-thresholds", "hard-lobbyist-meal-limit"]
COLD_PROBE_QUESTION_ID = "compliance-reporting-thresholds"

_SOURCE_LABEL_RE = re.compile(r"^\[([a-z_]+/[^\]\n]+\.md)\]", re.MULTILINE)
_SEARCH_HIT_RE = re.compile(r"^([a-z_]+/[^\s:]+\.md)(?: \[has Known issue\])?:", re.MULTILINE)


def call_cost(usage: dict, model: str = MODEL) -> float:
    price = PRICING[model]
    return (
        usage["input_tokens"] * price["input"]
        + usage["output_tokens"] * price["output"]
        + usage["cache_creation_input_tokens"] * price["cache_write"]
        + usage["cache_read_input_tokens"] * price["cache_read"]
    ) / 1_000_000


# --- Recording client --------------------------------------------------------


@dataclass
class CallRecord:
    latency_s: float
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    tools_offered: list[str]
    tool_calls: list[dict]  # [{name, input}]

    @property
    def usage(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
        }


class _RecordingMessages:
    def __init__(self, inner, trace):
        self._inner = inner
        self._trace = trace

    def create(self, **kwargs):
        # Sources the model has been shown so far (tool results in the
        # request), for failure classification.
        for message in kwargs.get("messages", []):
            if message["role"] != "user" or isinstance(message["content"], str):
                continue
            for block in message["content"]:
                if block.get("type") == "tool_result":
                    text = block.get("content", "")
                    self._trace["sources_seen"].update(_SOURCE_LABEL_RE.findall(text))
                    self._trace["search_hits"].update(_SEARCH_HIT_RE.findall(text))
        start = time.perf_counter()
        response = self._inner.messages.create(**kwargs)
        latency = time.perf_counter() - start
        usage = response.usage
        self._trace["calls"].append(
            CallRecord(
                latency_s=latency,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
                cache_read_input_tokens=usage.cache_read_input_tokens or 0,
                tools_offered=[t["name"] for t in kwargs.get("tools", [])],
                tool_calls=[
                    {"name": b.name, "input": b.input}
                    for b in response.content
                    if b.type == "tool_use"
                ],
            )
        )
        return response


class RecordingClient:
    def __init__(self, inner: anthropic.Anthropic):
        self.trace = {"calls": [], "sources_seen": set(), "search_hits": set()}
        self.messages = _RecordingMessages(inner, self.trace)


class LockedKnowledgeBase:
    """Serialises Chroma/embedding access across worker threads."""

    def __init__(self, kb: KnowledgeBase):
        self._kb = kb
        self._lock = threading.Lock()

    def search(self, *args, **kwargs):
        with self._lock:
            return self._kb.search(*args, **kwargs)


# --- One question run -------------------------------------------------------


def classify_failure(question, answer, checks: dict, trace: dict, strategy) -> str:
    """Best-effort label for why a run failed (reviewed by hand in the report)."""
    calls = trace["calls"]
    forced_wrapup = bool(calls) and set(calls[-1]["tools_offered"]) == {
        "decline_to_answer",
        "provide_answer",
    } and len(calls) > strategy.max_tool_rounds
    if forced_wrapup:
        return "wandering (round budget exhausted)"
    if "refused" in checks and not checks["refused"]:
        return "wrong refusal decision"
    if answer.refused and question.expect_refused is not True:
        return "wrongly refused"

    content_failed = [k for k, ok in checks.items() if not ok and k != "citations"]
    expected = question.expect_citation_contains
    if strategy.name == "long_context":
        surfaced = True  # everything is in context
    elif strategy.name == "glossary_inline" and all(e.startswith("glossary/") for e in expected):
        surfaced = True
    else:
        seen = set(trace["sources_seen"])
        surfaced = all(any(e in s for s in seen) for e in expected) if expected else True
    if not surfaced:
        return "retrieval miss"
    if checks.get("citations") is False and not content_failed:
        return "citation only (content correct)"
    if checks.get("citations") is False:
        return "wrong section cited"
    return "model reasoning error"


def run_one(strategy_name, question, question_set, run_index, inner_client, kb, ctx, strategy_options=None):
    recorder = RecordingClient(inner_client)
    strategy = build_strategy(strategy_name, lambda: kb, **(strategy_options or {}))
    error = None
    start = time.perf_counter()
    try:
        answer = handle_question(question.question, ctx, client=recorder, strategy=strategy)
    except Exception as exc:  # keep the batch going; record the failure
        answer, error = None, f"{type(exc).__name__}: {exc}"
    latency = time.perf_counter() - start

    calls = [{**asdict(c), "cost_usd": call_cost(c.usage)} for c in recorder.trace["calls"]]
    trace = {
        "calls": calls,
        "sources_seen": sorted(recorder.trace["sources_seen"]),
        "search_hits": sorted(recorder.trace["search_hits"]),
    }
    record = {
        "strategy": strategy_name,
        "question_set": question_set,
        "question_id": question.id,
        "run": run_index,
        "latency_s": latency,
        "n_calls": len(calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cache_creation_input_tokens": sum(c["cache_creation_input_tokens"] for c in calls),
        "cache_read_input_tokens": sum(c["cache_read_input_tokens"] for c in calls),
        "cost_usd": sum(c["cost_usd"] for c in calls),
        "trace": trace,
        "error": error,
    }
    if answer is None:
        record.update(passed=False, passed_content=False, checks={}, failure="error")
        return record

    outcome = grade(question, answer)
    content_checks = {k: v for k, v in outcome["checks"].items() if k != "citations"}
    record.update(
        passed=outcome["passed"],
        passed_content=all(content_checks.values()),
        checks=outcome["checks"],
        answer_text=answer.text,
        citations=answer.citations,
        refused=answer.refused,
        answer_category=answer.category,
        failure=None
        if outcome["passed"]
        else classify_failure(question, answer, outcome["checks"], trace, strategy),
    )
    return record


# --- Summaries ----------------------------------------------------------------


def _pct(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[index]


def summarize(records: list[dict]) -> dict:
    summary = {}
    for strategy in dict.fromkeys(r["strategy"] for r in records):
        rows = [r for r in records if r["strategy"] == strategy]
        by_question: dict[str, list[bool]] = {}
        for r in rows:
            by_question.setdefault(r["question_id"], []).append(r["passed"])

        def rate(subset, key="passed"):
            return sum(r[key] for r in subset) / len(subset) if subset else None

        modelled = [r for r in rows if r["n_calls"] > 0]  # injection pre-filter makes no calls
        s = {
            "runs": len(rows),
            "pass_rate_original": rate([r for r in rows if r["question_set"] == "original"]),
            "pass_rate_hard": rate([r for r in rows if r["question_set"] == "hard"]),
            "pass_rate_overall": rate(rows),
            "content_pass_rate_overall": rate(rows, "passed_content"),
            "content_pass_rate_hard": rate([r for r in rows if r["question_set"] == "hard"], "passed_content"),
            "questions_flipped": sorted(q for q, v in by_question.items() if len(set(v)) > 1),
            "failures": sorted(
                [
                    {"question_id": r["question_id"], "run": r["run"], "failure": r["failure"]}
                    for r in rows
                    if not r["passed"]
                ],
                key=lambda f: (f["question_id"], f["run"]),
            ),
        }
        for metric in [
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "n_calls",
            "cost_usd",
        ]:
            values = [r[metric] for r in modelled]
            s[f"{metric}_mean"] = statistics.mean(values) if values else 0
            s[f"{metric}_p95"] = _pct(values, 95)
        latencies = [r["latency_s"] for r in modelled]
        s["latency_p50"] = _pct(latencies, 50)
        s["latency_p95"] = _pct(latencies, 95)
        summary[strategy] = s
    return summary


def cache_breakdown(records: list[dict]) -> dict:
    """long_context calls split by cache state: cold (wrote the KB block)
    vs warm (read it)."""
    calls = [
        c
        for r in records
        if r["strategy"].startswith("long_context")
        for c in r["trace"]["calls"]
    ]
    cold = [c for c in calls if c["cache_creation_input_tokens"] > 0]
    warm = [c for c in calls if c["cache_creation_input_tokens"] == 0 and c["cache_read_input_tokens"] > 0]
    none = [c for c in calls if c["cache_creation_input_tokens"] == 0 and c["cache_read_input_tokens"] == 0]

    def stats(group):
        return {
            "calls": len(group),
            "cost_usd_mean": statistics.mean(c["cost_usd"] for c in group) if group else None,
            "latency_s_p50": _pct([c["latency_s"] for c in group], 50) if group else None,
            "latency_s_p95": _pct([c["latency_s"] for c in group], 95) if group else None,
        }

    return {"cold": stats(cold), "warm": stats(warm), "uncached": stats(none)}


def print_markdown(summary: dict, cache: dict) -> None:
    def f(v, fmt="{:.0%}"):
        return "-" if v is None else fmt.format(v)

    print("\n| strategy | pass orig | pass hard | pass all | content-only all | flipped | calls mean | in tok mean/p95 | out tok mean | cache read mean | cache write mean | latency p50/p95 s | $/question mean/p95 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, s in summary.items():
        print(
            f"| {name} | {f(s['pass_rate_original'])} | {f(s['pass_rate_hard'])} | {f(s['pass_rate_overall'])} "
            f"| {f(s['content_pass_rate_overall'])} | {len(s['questions_flipped'])} | {s['n_calls_mean']:.1f} "
            f"| {s['input_tokens_mean']:,.0f} / {s['input_tokens_p95']:,.0f} | {s['output_tokens_mean']:,.0f} "
            f"| {s['cache_read_input_tokens_mean']:,.0f} | {s['cache_creation_input_tokens_mean']:,.0f} "
            f"| {s['latency_p50']:.1f} / {s['latency_p95']:.1f} | ${s['cost_usd_mean']:.4f} / ${s['cost_usd_p95']:.4f} |"
        )
    print("\nlong_context cache state per call:", json.dumps(cache, indent=1))


# --- Main -----------------------------------------------------------------


def question_sets(dry_run: bool):
    sets = [("original", q) for q in QUESTIONS] + [("hard", q) for q in QUESTIONS_HARD]
    if dry_run:
        sets = [(s, q) for s, q in sets if q.id in DRY_RUN_QUESTION_IDS]
    return sets


def estimate_full_run(records: list[dict], n_runs: int, strategies: list[str]) -> dict:
    """Extrapolate the full run's cost from dry-run records."""
    n_questions = len(question_sets(dry_run=False))
    estimate = {}
    for strategy in strategies:
        rows = [r for r in records if r["strategy"] == strategy]
        if strategy == "long_context":
            # Bill the bulk at warm-cache rates, plus one cold KB write per
            # run (each run starts >5 min after the last).
            warm = [r for r in rows if r["cache_creation_input_tokens"] == 0] or rows
            per_q = statistics.mean(r["cost_usd"] for r in warm)
            cold_extra = max(r["cost_usd"] for r in rows) - per_q
            total = per_q * n_questions * n_runs + cold_extra * n_runs
        else:
            per_q = statistics.mean(r["cost_usd"] for r in rows)
            total = per_q * n_questions * n_runs
        estimate[strategy] = {"per_question_usd": per_q, "total_usd": total}
    cold_probe = [r for r in records if r["strategy"] == "long_context_cold_probe"]
    estimate["long_context_cold_probe"] = {
        "total_usd": (statistics.mean(r["cost_usd"] for r in cold_probe) if cold_probe else 0) * n_runs
    }
    estimate["TOTAL"] = {"total_usd": sum(v["total_usd"] for v in estimate.values())}
    return estimate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--strategies", nargs="*", default=STRATEGY_NAMES)
    parser.add_argument("--workers", type=int, default=len(STRATEGY_NAMES),
                        help="Strategies run in parallel; each strategy's questions stay sequential so long_context's cache stays warm.")
    args = parser.parse_args()
    n_runs = 1 if args.dry_run else args.runs

    inner = anthropic.Anthropic(max_retries=8)
    kb = LockedKnowledgeBase(KnowledgeBase())
    ctx = get_default_campaign_context()
    qs = question_sets(args.dry_run)
    cold_probe_q = next(q for _, q in question_sets(False) if q.id == COLD_PROBE_QUESTION_ID)

    records: list[dict] = []
    records_lock = threading.Lock()

    def run_strategy(strategy_name, run_index):
        for question_set, question in qs:
            record = run_one(strategy_name, question, question_set, run_index, inner, kb, ctx)
            status = "PASS" if record["passed"] else f"FAIL ({record['failure']})"
            print(f"[run {run_index}] {strategy_name:<16} {question.id:<48} {status}  ${record['cost_usd']:.4f}  {record['latency_s']:.1f}s", flush=True)
            with records_lock:
                records.append(record)
        if strategy_name == "long_context":
            # Guaranteed-cold measurement: a unique nonce changes the cached
            # prefix, so this call must write the whole KB block afresh.
            nonce = f"{run_index}-{time.time_ns()}"
            record = run_one(strategy_name, cold_probe_q, "cold_probe", run_index, inner, kb, ctx, {"cache_nonce": nonce})
            record["strategy"] = "long_context_cold_probe"
            print(f"[run {run_index}] long_context cold probe  ${record['cost_usd']:.4f}  {record['latency_s']:.1f}s", flush=True)
            with records_lock:
                records.append(record)

    started = datetime.now(timezone.utc)
    for run_index in range(1, n_runs + 1):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(lambda s: run_strategy(s, run_index), args.strategies))

    scored = [r for r in records if r["strategy"] != "long_context_cold_probe"]
    summary = summarize(scored)
    cache = cache_breakdown(records)
    print_markdown(summary, cache)

    output = {
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "pricing_usd_per_mtok": PRICING[MODEL],
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "dry_run": args.dry_run,
        "runs_per_question": n_runs,
        "strategies": args.strategies,
        "question_counts": {"original": len(QUESTIONS), "hard": len(QUESTIONS_HARD)},
        "summary": summary,
        "long_context_cache": cache,
        "cold_probe": [r for r in records if r["strategy"] == "long_context_cold_probe"],
        "records": scored,
    }
    if args.dry_run:
        output["full_run_estimate"] = estimate_full_run(records, args.runs, args.strategies)
        print("\nEstimated full-run cost (N=%d, %d questions):" % (args.runs, len(question_sets(False))))
        for name, e in output["full_run_estimate"].items():
            per_q = f"  (${e['per_question_usd']:.4f}/question)" if "per_question_usd" in e else ""
            print(f"  {name:<26} ${e['total_usd']:.2f}{per_q}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "-dryrun" if args.dry_run else ""
    out_path = RESULTS_DIR / f"{started.strftime('%Y%m%dT%H%M%SZ')}{suffix}.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
