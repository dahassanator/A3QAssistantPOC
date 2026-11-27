"""Report knowledge-base token counts: total, per category, and the 10
largest files - to answer whether the whole Alabama corpus fits in one
prompt (the `long_context` retrieval strategy).

Uses Anthropic's token-counting endpoint when ANTHROPIC_API_KEY is set,
otherwise a chars/4 estimate (labelled as such in the output).

Usage:
    python -m experiments.measure_corpus
"""

import os
import sys
from pathlib import Path

from assistant.knowledge_base import DEFAULT_DOCS_DIR
from assistant.orchestrator import MODEL

CONTEXT_WINDOW = 200_000  # claude-haiku-4-5
# Headroom left for the system prompt, tool definitions, the question, and
# a few rounds of tool calls/results - what long_context actually needs on
# top of the corpus itself.
HEADROOM = 20_000


def corpus_paths(docs_dir: Path = DEFAULT_DOCS_DIR) -> list[Path]:
    return sorted(docs_dir.glob("*/*.md"))


def count_tokens(paths: list[Path], docs_dir: Path = DEFAULT_DOCS_DIR):
    """Return ({relative_path: tokens}, method_label)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic(max_retries=5)
        # count_tokens counts a whole request, so subtract the overhead of
        # an empty-ish message to isolate each file's own tokens.
        def _count(text: str) -> int:
            return client.messages.count_tokens(
                model=MODEL, messages=[{"role": "user", "content": text}]
            ).input_tokens

        overhead = _count("x") - 1
        counts = {
            str(p.relative_to(docs_dir)): _count(p.read_text()) - overhead
            for p in paths
        }
        return counts, f"Anthropic count_tokens ({MODEL})"

    counts = {str(p.relative_to(docs_dir)): len(p.read_text()) // 4 for p in paths}
    return counts, "ESTIMATE: characters / 4 (no ANTHROPIC_API_KEY set)"


def main() -> int:
    paths = corpus_paths()
    counts, method = count_tokens(paths)
    total = sum(counts.values())

    by_category: dict[str, list[int]] = {}
    for rel, n in counts.items():
        by_category.setdefault(rel.split("/")[0], []).append(n)

    print(f"Token counts via {method}\n")
    print(f"Total: {total:,} tokens across {len(counts)} files\n")
    print(f"{'category':<20}{'files':>6}{'tokens':>10}{'share':>8}")
    for cat, ns in sorted(by_category.items(), key=lambda kv: -sum(kv[1])):
        print(f"{cat:<20}{len(ns):>6}{sum(ns):>10,}{sum(ns) / total:>8.1%}")

    print("\n10 largest files:")
    for rel, n in sorted(counts.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {n:>7,}  {rel}")

    budget = CONTEXT_WINDOW - HEADROOM
    print(
        f"\nFit: {total:,} / {CONTEXT_WINDOW:,} context window "
        f"({total / CONTEXT_WINDOW:.0%}); budget after {HEADROOM:,} headroom "
        f"is {budget:,} -> {'FITS' if total <= budget else 'DOES NOT FIT'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
