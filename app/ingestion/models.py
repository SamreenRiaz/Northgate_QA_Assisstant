"""Data shapes used by the ingestion pipeline."""
from dataclasses import dataclass, field


@dataclass
class Document:
    """One handbook file after parsing and cleaning."""

    doc_id: str  # from the manifest, e.g. "hr-leave-policy-v2"
    title: str  # e.g. "Leave Policy v2"
    text: str  # clean Markdown-style text of the whole file
    metadata: dict = field(default_factory=dict)  # manifest fields: category, owner, status...


@dataclass
class Chunk:
    """A small piece of a Document: the unit we search and cite."""

    chunk_id: str  # "<doc_id>#<number>", e.g. "hr-leave-policy-v2#3"
    doc_id: str  # which Document it came from
    text: str  # the passage itself
    section: str  # heading path, e.g. "Leave Policy v2 > Sick leave"
    metadata: dict = field(default_factory=dict)  # copied from its Document

