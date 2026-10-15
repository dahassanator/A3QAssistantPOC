"""Experimental retrieval strategies (research branch, not the default).

Each strategy changes only how law, guidance, glossary and how-to knowledge
reaches the model. `handle_question` keeps everything else identical across
strategies - safety pre-checks, the campaign data tools, the terminal tools,
the round budget/wrap-up, and `_build_final_answer` - so a comparison between
them measures retrieval and nothing else. The default strategy, `RagCurrent`,
lives in the orchestrator; these follow its shape:

- `long_context`: no retrieval tool; the whole knowledge base sits in the
  system prompt behind an Anthropic prompt-cache breakpoint. Citations are
  derived from the section/opinion numbers the answer cites.
- `agentic_nav` / `agentic_nav_10`: the model browses the markdown files
  with list/read/grep tools (5 or 10 tool rounds). Citations are the files
  it actually read.
- `hybrid`: embedding search fused with BM25 keyword search via
  reciprocal-rank fusion, same top-k and result format as today.
- `glossary_inline`: today's RAG, but the glossary is pasted into the
  system prompt and excluded from search.

Every strategy attaches `_FLAGS.md` "Known issue" caveats wherever a flagged
file's text reaches the model.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Callable

from assistant.knowledge_base import (
    DEFAULT_DOCS_DIR,
    KnowledgeBase,
    Passage,
    load_flags,
    match_flag,
)
from assistant.orchestrator import (
    CANVASSING_TOOL,
    CONTRIBUTIONS_TOOL,
    DEADLINES_TOOL,
    DECLINE_TOOL,
    EXPENDITURES_TOOL,
    MAX_TOOL_ROUNDS,
    PROVIDE_ANSWER_TOOL,
    RagCurrent,
    format_passages,
)

DATA_TOOL_DEFS = [CONTRIBUTIONS_TOOL, EXPENDITURES_TOOL, CANVASSING_TOOL, DEADLINES_TOOL]

# --- Corpus access (shared by the non-embedding strategies) ---------------


@lru_cache(maxsize=None)
def _corpus(docs_dir: Path = DEFAULT_DOCS_DIR) -> dict[str, str]:
    """{relative path: file text} for every knowledge-base document, sorted
    by path so anything built from it (e.g. the cached prompt block) is
    byte-stable across calls."""
    return {
        str(p.relative_to(docs_dir)): p.read_text()
        for p in sorted(docs_dir.glob("*/*.md"))
    }


@lru_cache(maxsize=None)
def _flags(docs_dir: Path = DEFAULT_DOCS_DIR) -> tuple[tuple[str, str], ...]:
    return tuple(load_flags(docs_dir))


def _flag_for(path: str) -> str | None:
    return match_flag(list(_flags()), path)


def _render_document(path: str, text: str) -> str:
    """One document in the same `[source]` / `Known issue:` / text shape the
    search tool has always used, so every strategy shows the model the same
    labels."""
    return format_passages([Passage(text=text, source=path, category=path.split("/")[0], flag=_flag_for(path))])


_TITLE_RE = re.compile(r'^title:\s*"?(.+?)"?\s*$', re.MULTILINE)
_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _title(text: str) -> str:
    """Front-matter title, else the first `# ` heading (glossary/how-to
    files have no front matter)."""
    match = _TITLE_RE.search(text[:2000]) or _HEADING_RE.search(text)
    return match.group(1) if match else ""


# --- System-prompt edits ----------------------------------------------------
#
# The base prompt is written around search_knowledge_base. Strategies that
# remove or change that tool swap only the sentences that name it; the scope,
# safety, numbering and Known-issue rules stay verbatim.

_SEARCH_TERMINOLOGY = (
    "For political or campaign-finance terminology and for platform how-to "
    "questions, call search_knowledge_base and answer from the retrieved "
    "passages rather than from memory. "
)
_SEARCH_COMBINE = "call both search_knowledge_base and the relevant data tool"
_SEARCH_CITE = "retrieved via search_knowledge_base, cite"
_PROVIDE_ANSWER_HINT = "search_knowledge_base / data tool calls"


def _rewrite(base_system: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        if old not in base_system:
            raise ValueError(
                f"System prompt no longer contains {old!r}; update "
                "retrieval_strategies to match the orchestrator's template."
            )
        base_system = base_system.replace(old, new)
    return base_system


def _provide_answer_tool(hint: str) -> dict:
    tool = dict(PROVIDE_ANSWER_TOOL)
    tool["description"] = tool["description"].replace(_PROVIDE_ANSWER_HINT, hint)
    return tool


# --- Citations derived from answer text ------------------------------------

_SECTION_RE = re.compile(r"\b((?:17-5|36-25)-\d+(?:\.\d+)?)(?![\d.]*\d)")
_AGO_RE = re.compile(r"\b(\d{2,4}-\d{3,5})\b")
_PATH_RE = re.compile(r"\b([a-z_]+/[\w.\-]+\.md)\b")


def citations_from_text(text: str) -> list[str]:
    """Map the sources an answer names to knowledge-base paths: statute
    sections (`§ 17-5-8(a)(1)` -> `fcpa_statute/17-5-8_...md`), AG opinion
    numbers (`94-00227` -> `ag_opinions/AGO_94-00227_...md`), and any
    knowledge-base path quoted verbatim."""
    corpus = _corpus()
    found: list[str] = []

    def add(path: str) -> None:
        if path not in found:
            found.append(path)

    for section in _SECTION_RE.findall(text):
        for path in corpus:
            if path.split("/")[-1].startswith(f"{section}_"):
                add(path)
    for number in _AGO_RE.findall(text):
        for path in corpus:
            if path.startswith(f"ag_opinions/AGO_{number}_"):
                add(path)
    for path in _PATH_RE.findall(text):
        if path in corpus:
            add(path)
    return found


# --- Strategies -------------------------------------------------------------


class LongContext:
    """Whole knowledge base in the system prompt, no retrieval tool."""

    name = "long_context"
    max_tool_rounds = MAX_TOOL_ROUNDS

    def __init__(self, cache_nonce: str = ""):
        # A non-empty nonce changes the cached prefix, forcing a cold cache
        # write - used by the comparison to measure the cold-cache cost.
        self._cache_nonce = cache_nonce

    @staticmethod
    @lru_cache(maxsize=None)
    def _kb_block() -> str:
        documents = "\n\n".join(
            f"<document>\n{_render_document(path, text)}\n</document>"
            for path, text in _corpus().items()
        )
        return f"<knowledge_base>\n{documents}\n</knowledge_base>"

    def system(self, base_system: str):
        instructions = _rewrite(
            base_system,
            [
                (
                    _SEARCH_TERMINOLOGY,
                    "For political or campaign-finance terminology and for "
                    "platform how-to questions, answer from the documents in "
                    "the <knowledge_base> block above rather than from memory. ",
                ),
                (
                    _SEARCH_COMBINE,
                    "check both the <knowledge_base> documents and call the "
                    "relevant data tool",
                ),
                (_SEARCH_CITE, "in the <knowledge_base> block, cite"),
            ],
        )
        kb_text = self._kb_block()
        if self._cache_nonce:
            kb_text = f"<!-- cache run {self._cache_nonce} -->\n{kb_text}"
        # Documents first (behind the cache breakpoint), instructions after,
        # so the ~100k-token block is a stable prefix every call can reuse.
        return [
            {"type": "text", "text": kb_text, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": instructions},
        ]

    def tools(self) -> list[dict]:
        return [*DATA_TOOL_DEFS, DECLINE_TOOL, _provide_answer_tool("data tool calls")]

    def finish_tools(self) -> list[dict]:
        return [DECLINE_TOOL, _provide_answer_tool("data tool calls")]

    def handle_tool(self, name: str, tool_input: dict) -> tuple[str, list[str]]:
        return f"Unknown tool: {name}", []

    def final_citations(self, citations: list[str], answer_text: str) -> list[str]:
        return citations + [c for c in citations_from_text(answer_text) if c not in citations]


LIST_CATEGORIES_TOOL = {
    "name": "list_categories",
    "description": (
        "List the knowledge base's document categories (folders) with how "
        "many documents each holds: Alabama campaign-finance statute, ethics "
        "law, Secretary of State guidance, AG opinions, Ethics Commission "
        "guidance, glossary of terms, and platform how-tos."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

LIST_DOCUMENTS_TOOL = {
    "name": "list_documents",
    "description": "List every document in one category: its path and title.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "A category from list_categories."}
        },
        "required": ["category"],
    },
}

READ_DOCUMENT_TOOL = {
    "name": "read_document",
    "description": (
        "Read one knowledge-base document in full, by the path that "
        "list_documents or search_text returned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "e.g. fcpa_statute/17-5-8_reports_of_contributions_and_expenditures.md"}
        },
        "required": ["path"],
    },
}

SEARCH_TEXT_TOOL = {
    "name": "search_text",
    "description": (
        "Case-insensitive keyword or regular-expression search across every "
        "knowledge-base document. Returns matching paths with short snippets "
        "around each match - read_document the ones you need."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A keyword, phrase, or regex."}
        },
        "required": ["query"],
    },
}

NAV_TOOLS = [LIST_CATEGORIES_TOOL, LIST_DOCUMENTS_TOOL, READ_DOCUMENT_TOOL, SEARCH_TEXT_TOOL]

SEARCH_TEXT_MAX_MATCHES = 25
SEARCH_TEXT_SNIPPET_CHARS = 100


class AgenticNav:
    """The model browses the markdown files itself."""

    name = "agentic_nav"

    def __init__(self, max_tool_rounds: int = MAX_TOOL_ROUNDS):
        self.max_tool_rounds = max_tool_rounds
        if max_tool_rounds != MAX_TOOL_ROUNDS:
            self.name = f"agentic_nav_{max_tool_rounds}"

    def system(self, base_system: str):
        return _rewrite(
            base_system,
            [
                (
                    _SEARCH_TERMINOLOGY,
                    "For political or campaign-finance terminology and for "
                    "platform how-to questions, find and read the relevant "
                    "knowledge-base documents with list_categories, "
                    "list_documents, search_text and read_document, and answer "
                    "from what you read rather than from memory. ",
                ),
                (
                    _SEARCH_COMBINE,
                    "read the relevant knowledge-base documents and call the "
                    "relevant data tool",
                ),
                (_SEARCH_CITE, "read via read_document, cite"),
            ],
        )

    def tools(self) -> list[dict]:
        return [
            *NAV_TOOLS,
            *DATA_TOOL_DEFS,
            DECLINE_TOOL,
            _provide_answer_tool("knowledge-base / data tool calls"),
        ]

    def finish_tools(self) -> list[dict]:
        return [DECLINE_TOOL, _provide_answer_tool("knowledge-base / data tool calls")]

    def handle_tool(self, name: str, tool_input: dict) -> tuple[str, list[str]]:
        corpus = _corpus()
        if name == "list_categories":
            counts: dict[str, int] = {}
            for path in corpus:
                counts[path.split("/")[0]] = counts.get(path.split("/")[0], 0) + 1
            return "\n".join(f"{cat} ({n} documents)" for cat, n in counts.items()), []

        if name == "list_documents":
            category = tool_input.get("category", "").strip().strip("/")
            rows = [
                f"{path} - {_title(text)}"
                for path, text in corpus.items()
                if path.split("/")[0] == category
            ]
            return ("\n".join(rows) or f"No category named {category!r}."), []

        if name == "read_document":
            path = tool_input.get("path", "").strip().lstrip("/")
            path = path.removeprefix("knowledge_base/")
            # Only exact corpus paths are readable - no traversal.
            if path not in corpus:
                return f"No document at {path!r}. Use list_documents or search_text to find paths.", []
            return _render_document(path, corpus[path]), [path]

        if name == "search_text":
            return search_text(tool_input.get("query", "")), []

        return f"Unknown tool: {name}", []

    def final_citations(self, citations: list[str], answer_text: str) -> list[str]:
        return citations


def search_text(query: str) -> str:
    """Grep the corpus: regex if `query` compiles, literal text otherwise."""
    corpus = _corpus()
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    if not query.strip():
        return "Empty query."

    lines = []
    total = 0
    for path, text in corpus.items():
        for match in pattern.finditer(text):
            total += 1
            if len(lines) >= SEARCH_TEXT_MAX_MATCHES:
                continue
            start = max(0, match.start() - SEARCH_TEXT_SNIPPET_CHARS)
            end = min(len(text), match.end() + SEARCH_TEXT_SNIPPET_CHARS)
            snippet = " ".join(text[start:end].split())
            flag = " [has Known issue]" if _flag_for(path) else ""
            lines.append(f"{path}{flag}: ...{snippet}...")
    if not lines:
        return f"No matches for {query!r}."
    more = f"\n({total - len(lines)} more matches not shown - narrow the query.)" if total > len(lines) else ""
    return "\n".join(lines) + more


_BM25_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")


def bm25_tokenize(text: str) -> list[str]:
    """Lowercase word tokens that keep `17-5-8` / `17-5-15.1` intact."""
    return _BM25_TOKEN_RE.findall(text.lower())


@lru_cache(maxsize=None)
def _bm25_index():
    from rank_bm25 import BM25Okapi

    paths = list(_corpus())
    return paths, BM25Okapi([bm25_tokenize(_corpus()[p]) for p in paths])


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda item: -scores[item])


class Hybrid(RagCurrent):
    """Embedding search + BM25, merged with reciprocal-rank fusion."""

    name = "hybrid"
    TOP_K = 3
    CANDIDATES = 20

    def handle_tool(self, name: str, tool_input: dict) -> tuple[str, list[str]]:
        query = tool_input["query"]
        dense = [p.source for p in self._get_knowledge_base().search(query, k=self.CANDIDATES)]
        paths, bm25 = _bm25_index()
        scores = bm25.get_scores(bm25_tokenize(query))
        keyword = [paths[i] for i in sorted(range(len(paths)), key=lambda i: -scores[i])[: self.CANDIDATES]]
        top = reciprocal_rank_fusion([dense, keyword])[: self.TOP_K]
        corpus = _corpus()
        passages = [
            Passage(text=corpus[p], source=p, category=p.split("/")[0], flag=_flag_for(p))
            for p in top
        ]
        return format_passages(passages), top


class GlossaryInline(RagCurrent):
    """Today's RAG with the glossary pasted into the prompt instead."""

    name = "glossary_inline"
    INLINE_CATEGORY = "glossary"

    def system(self, base_system: str):
        glossary = "\n\n".join(
            _render_document(path, text)
            for path, text in _corpus().items()
            if path.startswith(f"{self.INLINE_CATEGORY}/")
        )
        instructions = _rewrite(
            base_system,
            [
                (
                    _SEARCH_TERMINOLOGY,
                    "For political or campaign-finance terminology, answer from "
                    "the glossary definitions in the <glossary> block at the end "
                    "of this prompt when they cover the term; otherwise, and for "
                    "platform how-to questions, call search_knowledge_base and "
                    "answer from the retrieved passages rather than from memory. ",
                ),
            ],
        )
        return f"{instructions}\n\n<glossary>\n{glossary}\n</glossary>"

    def handle_tool(self, name: str, tool_input: dict) -> tuple[str, list[str]]:
        passages = self._get_knowledge_base().search(
            tool_input["query"], exclude_categories=[self.INLINE_CATEGORY]
        )
        return format_passages(passages), [p.source for p in passages]

    def final_citations(self, citations: list[str], answer_text: str) -> list[str]:
        # Glossary entries never come back from search here, so credit any
        # the answer names (by path or by section/opinion number).
        return citations + [c for c in citations_from_text(answer_text) if c not in citations]


STRATEGY_NAMES = [
    "rag_current",
    "long_context",
    "agentic_nav",
    "agentic_nav_10",
    "hybrid",
    "glossary_inline",
]


def build_strategy(name: str, get_knowledge_base: Callable[[], KnowledgeBase], **options):
    if name == "rag_current":
        return RagCurrent(get_knowledge_base)
    if name == "long_context":
        return LongContext(**options)
    if name == "agentic_nav":
        return AgenticNav()
    if name == "agentic_nav_10":
        return AgenticNav(max_tool_rounds=10)
    if name == "hybrid":
        return Hybrid(get_knowledge_base)
    if name == "glossary_inline":
        return GlossaryInline(get_knowledge_base)
    raise ValueError(f"Unknown retrieval strategy {name!r}; expected one of {STRATEGY_NAMES}")
