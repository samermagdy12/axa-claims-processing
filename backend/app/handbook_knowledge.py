"""Handbook ingestion, semantic chunking, and persistent vector storage."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from pathlib import Path
from typing import Any, Protocol

from docx import Document
from pypdf import PdfReader


class HandbookKnowledgeError(RuntimeError):
    """Raised when the external handbook knowledge store cannot be used."""


@dataclass(frozen=True)
class HandbookChunk:
    chunk_id: str
    content: str
    metadata: dict[str, Any]


RULE_CATEGORIES = frozenset({
    "DOCUMENT_REQUIREMENT", "POLICY_VALIDATION", "COVERAGE", "EXCLUSION",
    "LIMIT", "RISK", "FRAUD", "HUMAN_REVIEW", "SETTLEMENT", "OTHER",
})


class VectorStore(Protocol):
    def upsert(self, chunks: list[HandbookChunk], embeddings: list[list[float]]) -> None: ...

    def query(self, embedding: list[float], limit: int) -> list[dict[str, Any]]: ...


def load_handbook_chunks(source_path: str | Path, max_chunk_chars: int = 2200) -> list[HandbookChunk]:
    """Read supported handbook files and retain headings/clause identifiers per chunk."""
    source = Path(source_path)
    if not source.exists():
        raise HandbookKnowledgeError(f"Handbook source does not exist: {source}")
    paths = [source] if source.is_file() else sorted(path for path in source.rglob("*") if path.suffix.lower() in {".md", ".txt", ".pdf", ".docx"})
    chunks: list[HandbookChunk] = []
    for path in paths:
        text, pages = _read_handbook_file(path)
        chunks.extend(chunk_handbook_text(text, source=str(path), page_by_text=pages, max_chunk_chars=max_chunk_chars))
    if not chunks:
        raise HandbookKnowledgeError("No readable handbook content was found")
    return chunks


def chunk_handbook_text(text: str, source: str, page_by_text: dict[str, int] | None = None, max_chunk_chars: int = 2200) -> list[HandbookChunk]:
    """Split on document structure and paragraphs, never arbitrary character slices."""
    state: dict[str, str] = {}
    sections: list[tuple[str, dict[str, str]]] = []
    current: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        heading = _heading(line)
        clause = _clause_identifier(line)
        if heading or clause:
            # Keep a heading with its first rule/paragraph, but finish an earlier
            # complete rule before beginning a new heading or clause.
            if current and _has_substantive_content(current):
                sections.append(("\n".join(current).strip(), dict(state)))
                current = []
            if heading:
                level, title = heading
                key = {1: "chapter", 2: "section"}.get(level, "subsection")
                state[key] = title
                state.pop("rule_identifier", None)
                if level <= 1:
                    state.pop("section", None)
                    state.pop("subsection", None)
                elif level == 2:
                    state.pop("subsection", None)
            if clause:
                state["rule_identifier"] = clause
            current.append(line)
        else:
            current.append(line)
    if current:
        sections.append(("\n".join(current).strip(), dict(state)))

    chunks: list[HandbookChunk] = []
    for section_text, metadata in sections:
        for content in _split_section(section_text, max_chunk_chars):
            if not content:
                continue
            item_metadata = {"source": source, **metadata}
            item_metadata.update(_rule_metadata(content, item_metadata))
            if page_by_text:
                page = page_by_text.get(content)
                if page is not None:
                    item_metadata["page"] = page
            identifier = hashlib.sha256(f"{source}\0{content}".encode("utf-8")).hexdigest()[:24]
            chunks.append(HandbookChunk(chunk_id=f"handbook-{identifier}", content=content, metadata=item_metadata))
    return chunks


def _has_substantive_content(lines: list[str]) -> bool:
    # Handbook clauses commonly put their complete rule on the same line as
    # the clause label.  That line is substantive content, not just a marker.
    return any(line.strip() and not _heading(line) for line in lines)


def _read_handbook_file(path: Path) -> tuple[str, dict[str, int] | None]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8"), None
    if suffix == ".docx":
        document = Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs), None
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        page_texts = {page.extract_text() or "": number for number, page in enumerate(reader.pages, start=1)}
        return "\n\n".join(page_texts), page_texts
    raise HandbookKnowledgeError(f"Unsupported handbook format: {path.suffix}")


def _heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return len(match.group(1)), re.sub(r"[*_`]+", "", match.group(2)).strip()


def _clause_identifier(line: str) -> str | None:
    clean = re.sub(r"[*_`]+", "", line)
    match = re.search(r"\b(?:clause|rule|policy)\s+([A-Za-z]*\.?\d+(?:\.\d+)*(?:[-A-Za-z0-9]*)?)\b", clean, re.IGNORECASE)
    return match.group(1) if match else None


def _split_section(section: str, max_chunk_chars: int) -> list[str]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", section) if item.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        # A very long paragraph is retained intact rather than cutting a rule mid-sentence.
        addition = len(paragraph) + (2 if current else 0)
        if current and size + addition > max_chunk_chars:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(paragraph)
        size += addition
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _rule_metadata(content: str, context: dict[str, Any]) -> dict[str, str]:
    """Classify a clause at ingestion so retrieval cannot blur rule purposes.

    This is deliberately conservative: an ambiguous rule is OTHER and therefore
    cannot independently authorize a rejection or settlement.
    """
    text = f"{context.get('chapter', '')} {context.get('section', '')} {content}".casefold()
    source = Path(str(context.get("source", ""))).stem.casefold()
    product = next((name for name in ("health", "motor", "property", "travel") if name in source or name in text), "")
    products = "ALL" if "universal exclusion" in text or "general rules" in text else (product.upper() if product else "ALL")
    if any(term in text for term in ("auto-approve", "auto-approval", "approval authority")):
        category = "SETTLEMENT"
    elif "required document" in text or "document" in text and any(term in text for term in ("invoice", "report", "receipt", "photograph", "licence", "registration")):
        category = "DOCUMENT_REQUIREMENT"
    elif any(term in text for term in ("fraud", "duplicate", "attempted override")):
        category = "FRAUD" if "fraud" in text else "RISK"
    elif any(term in text for term in ("route to a human", "human assessor", "specialist review")):
        category = "HUMAN_REVIEW"
    elif any(term in text for term in ("annual limit", "sub-limit", "deductible", "above egp", "cap")):
        category = "LIMIT"
    elif any(term in text for term in ("policy not in force", "policy period", "policy is active", "waiting period")):
        category = "POLICY_VALIDATION"
    elif any(term in text for term in ("excluded", "not covered", "no cover", "rejected under this clause")):
        category = "EXCLUSION"
    elif any(term in text for term in ("cover includes", "is covered", "cover applies")):
        category = "COVERAGE"
    else:
        category = "OTHER"
    return {"rule_category": category, "applies_to_products": products}


class ChromaHandbookVectorStore:
    """Persistent Chroma store; imported lazily so normal API startup has no optional dependency cost."""

    def __init__(self, directory: str | Path, collection_name: str):
        try:
            import chromadb
        except ImportError as exc:
            raise HandbookKnowledgeError("chromadb is required for the handbook knowledge base; install backend requirements") from exc
        self._collection = chromadb.PersistentClient(path=str(directory)).get_or_create_collection(name=collection_name)

    def upsert(self, chunks: list[HandbookChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise HandbookKnowledgeError("Handbook chunks and embeddings have different counts")
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[_chroma_metadata(chunk.metadata) for chunk in chunks],
            embeddings=embeddings,
        )

    def query(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        response = self._collection.query(query_embeddings=[embedding], n_results=limit, include=["documents", "metadatas", "distances"])
        return [
            {"chunk_id": identifier, "content": content, "score": 1.0 / (1.0 + float(distance)), "metadata": metadata or {}}
            for identifier, content, metadata, distance in zip(response["ids"][0], response["documents"][0], response["metadatas"][0], response["distances"][0])
        ]


def _chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {key: value for key, value in metadata.items() if isinstance(value, (str, int, float, bool))}
