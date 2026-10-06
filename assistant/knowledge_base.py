"""Semantic search over the authored knowledge base (glossary + platform how-tos).

Markdown files under `knowledge_base/<category>/` are split into chunks,
embedded with sentence-transformers and stored in Chroma.
`KnowledgeBase.search` is the retrieval seam the orchestrator's search tool
calls.

Chunking matters because the embedding model only reads the first 256
tokens of its input and silently drops the rest - embedding whole files
left most of a long statute (e.g. the "contribution" definition in
§ 17-5-2) unsearchable. Each chunk is prefixed with its file's title so it
still says what statute or doc it came from. A file's YAML frontmatter is
not embedded, but is attached to every passage returned from that file:
its notes carry caveats the model needs (e.g. an AG opinion's mapping from
pre-2006 § 17-22A-x numbers to current § 17-5-x ones).

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
# Words per chunk, title excluded. Legal text runs ~1.4 tokens per word, so
# this plus the title stays inside the model's 256-token window.
CHUNK_WORDS = 140
# Chunks either side of a hit returned with it, so a statutory list item
# arrives with its lead-in (e.g. "(3) CONTRIBUTION.") rather than orphaned.
NEIGHBOR_CHUNKS = 1

FLAGS_FILENAME = "_FLAGS.md"
_FLAG_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|$")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_TITLE_RE = re.compile(r'^title:\s*"?(.*?)"?\s*$', re.MULTILINE)
_DESCRIPTION_RE = re.compile(r'^description:\s*"?(.*?)"?\s*$', re.MULTILINE)
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _split_to_fit(text: str, max_words: int) -> list[str]:
    """Split one oversized paragraph by lines (tables, lists), then by words."""
    pieces = []
    for line in text.splitlines():
        words = line.split()
        if len(words) <= max_words:
            pieces.append(line)
            continue
        for i in range(0, len(words), max_words):
            pieces.append(" ".join(words[i : i + max_words]))
    return pieces


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter block including its --- fences, body)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return match.group(0).strip(), text[match.end() :]


def chunk_document(text: str, max_words: int = CHUNK_WORDS) -> list[str]:
    """Split a knowledge-base file's body into title-prefixed chunks.

    Each chunk is <= max_words plus the title. Paragraphs are packed
    greedily so a chunk never splits mid-paragraph unless that paragraph
    alone is too long. Frontmatter is dropped (see `split_frontmatter`)
    except its description, which leads the first chunk: it's a one-line
    summary of the whole file and often the best match for a query.
    """
    title = None
    pieces = []
    frontmatter, text = split_frontmatter(text)
    if frontmatter:
        title_match = _TITLE_RE.search(frontmatter)
        title = title_match.group(1) if title_match else None
        description_match = _DESCRIPTION_RE.search(frontmatter)
        if description_match:
            pieces.append(description_match.group(1))
    if title is None:
        heading = _HEADING_RE.search(text)
        title = heading.group(1).strip() if heading else None

    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        # The file's own "# Title" heading would repeat the chunk prefix.
        if not paragraph or (title and paragraph.lstrip("# ").strip() == title):
            continue
        if len(paragraph.split()) <= max_words:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_to_fit(paragraph, max_words))

    chunks, current, current_words = [], [], 0
    for piece in pieces:
        words = len(piece.split())
        if current and current_words + words > max_words:
            chunks.append("\n\n".join(current))
            current, current_words = [], 0
        current.append(piece)
        current_words += words
    if current:
        chunks.append("\n\n".join(current))

    if title:
        chunks = [f"{title}\n\n{chunk}" for chunk in chunks]
    return chunks


@dataclass
class Passage:
    text: str
    source: str
    category: str
    flag: str | None = None


def _join_chunks(chunks: list[str]) -> str:
    """Rejoin adjacent chunks of one file, keeping the title prefix only once."""
    title = chunks[0].split("\n\n", 1)[0]
    bodies = [
        chunk[len(title) :].lstrip("\n") if i and chunk.startswith(title) else chunk
        for i, chunk in enumerate(chunks)
    ]
    return "\n\n".join(bodies)


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
        ids, documents, metadatas = [], [], []
        for path in sorted(docs_dir.glob("*/*.md")):
            source = str(path.relative_to(docs_dir))
            text = path.read_text()
            frontmatter, _ = split_frontmatter(text)
            for i, chunk in enumerate(chunk_document(text)):
                ids.append(f"{source}#{i}")
                documents.append(chunk)
                metadatas.append(
                    {
                        "category": path.parent.name,
                        "source": source,
                        "chunk": i,
                        "frontmatter": frontmatter,
                    }
                )

        # The collection persists between runs, so drop anything this ingest
        # didn't produce (whole-file entries from before chunking, or trailing
        # chunks of a file that has since shrunk).
        stale = set(self._collection.get(include=[])["ids"]) - set(ids)
        if stale:
            self._collection.delete(ids=list(stale))
        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

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

    def search(self, query: str, k: int = 5) -> list[Passage]:
        """Return the best-matching passage from each of the top k files.

        One passage per file: otherwise a long file whose chunks all
        resemble the query (e.g. the SOS candidate guidelines) can fill
        every slot and crowd out the statute that actually answers it.
        """
        result = self._collection.query(
            query_texts=[query],
            n_results=min(k * 5, self._collection.count()),
        )
        passages = []
        seen_sources: set[str] = set()
        for meta in result["metadatas"][0]:
            source, hit = meta["source"], meta["chunk"]
            if source in seen_sources:
                continue
            seen_sources.add(source)
            window_ids = [
                f"{source}#{i}"
                for i in range(hit - NEIGHBOR_CHUNKS, hit + NEIGHBOR_CHUNKS + 1)
                if i >= 0
            ]
            window = self._collection.get(ids=window_ids, include=["documents", "metadatas"])
            ordered = sorted(
                zip(window["metadatas"], window["documents"]), key=lambda m: m[0]["chunk"]
            )
            body = _join_chunks([doc for _, doc in ordered])
            passages.append(
                Passage(
                    text=f"{meta['frontmatter']}\n\n{body}" if meta["frontmatter"] else body,
                    source=source,
                    category=meta["category"],
                    flag=self._flag_for(source),
                )
            )
            if len(passages) == k:
                break
        return passages
