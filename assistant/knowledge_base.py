"""Semantic search over the authored knowledge base (glossary + platform how-tos).

Markdown files under `knowledge_base/<category>/` are embedded with
sentence-transformers and stored in Chroma. `KnowledgeBase.search` is the
retrieval seam the orchestrator's search tool calls.

`_FLAGS.md` at the knowledge base root documents known accuracy/provenance
caveats on individual source files (see its "Quick reference" table). It is
not itself ingested as a searchable passage; instead `_load_flags` parses
that table so `search` can attach the matching caveat to any passage whose
source it covers.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DEFAULT_DOCS_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"
DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / ".chroma"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

FLAGS_FILENAME = "_FLAGS.md"
_FLAG_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|$")


@dataclass
class Passage:
    text: str
    source: str
    category: str
    flag: str | None = None


class KnowledgeBase:
    def __init__(self, persist_dir=DEFAULT_PERSIST_DIR, docs_dir=DEFAULT_DOCS_DIR):
        client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            ),
        )
        docs_dir = Path(docs_dir)
        self._ingest(docs_dir)
        self._flags = self._load_flags(docs_dir)

    def _ingest(self, docs_dir: Path) -> None:
        paths = sorted(docs_dir.glob("*/*.md"))
        self._collection.upsert(
            ids=[str(p.relative_to(docs_dir)) for p in paths],
            documents=[p.read_text() for p in paths],
            metadatas=[{"category": p.parent.name} for p in paths],
        )

    def _load_flags(self, docs_dir: Path) -> list[tuple[str, str]]:
        """Parse `_FLAGS.md`'s quick-reference table into (source, flag) pairs.

        Only rows naming a single file are captured (exact path, or a
        `path/prefix_...` truncation treated as a startswith match). Rows
        that group several files or a whole directory are skipped here -
        those are broader caveats (e.g. pre-2006 statute renumbering) that
        belong in the system prompt as a general rule instead.
        """
        path = docs_dir / FLAGS_FILENAME
        if not path.exists():
            return []
        flags = []
        for line in path.read_text().splitlines():
            match = _FLAG_ROW_RE.match(line)
            if not match:
                continue
            flags.append(match.groups())
        return flags

    def _flag_for(self, source: str) -> str | None:
        for pattern, flag in self._flags:
            if pattern.endswith("..."):
                if source.startswith(pattern[: -len("...")]):
                    return flag
            elif source == pattern:
                return flag
        return None

    def search(self, query: str, k: int = 3) -> list[Passage]:
        result = self._collection.query(query_texts=[query], n_results=k)
        return [
            Passage(
                text=text,
                source=source,
                category=meta["category"],
                flag=self._flag_for(source),
            )
            for source, text, meta in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0]
            )
        ]
