"""Split Documents into Chunks at Markdown headings, with a size limit.

Every heading starts a new section. A section's "path" is the list of headings it sits
under, e.g. ["Travel Policy", "4. Limits", "4.2 Hotels"]. Headings with no text of their
own (like a bare "# Title") do not become chunks; they only appear in the path of the
sections below them. Sections longer than MAX_WORDS are split between lines.
"""
import re

from app.ingestion.models import Chunk, Document

MAX_WORDS = 200
HEADING = re.compile(r"^(#{1,6}) (.+)$")  # a line that STARTS with 1-6 '#' and a space

# One section: (heading path, the section's lines including its own heading line).
Section = tuple[list[str], list[str]]


def chunk_document(doc: Document) -> list[Chunk]:
    """Turn one Document into Chunks, numbered <doc_id>#0, #1, ..."""
    chunks = []
    for path, lines in split_into_sections(doc.text):
        for text in pack_lines(lines, MAX_WORDS):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{len(chunks)}",
                    doc_id=doc.doc_id,
                    text=text,
                    section=" > ".join(path),
                    metadata={"title": doc.title, **doc.metadata},  # a new dict per chunk
                )
            )
    return chunks


def chunk_documents(docs: list[Document]) -> list[Chunk]:
    """Chunk every Document, keeping document order."""
    return [chunk for doc in docs for chunk in chunk_document(doc)]


def split_into_sections(text: str) -> list[Section]:
    """Cut text at every heading and record the heading path of each piece.

    A heading with N '#' keeps the first N-1 names of the current path and adds its own.
    Sections without body text are skipped.
    """
    sections: list[Section] = []
    path: list[str] = []
    lines: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match is None:
            lines.append(line)
            continue
        if has_body(lines):
            sections.append((path, lines))
        level = len(match.group(1))
        path = path[: level - 1] + [match.group(2).strip()]
        lines = [line]
    if has_body(lines):
        sections.append((path, lines))
    return sections


def pack_lines(lines: list[str], max_words: int) -> list[str]:
    """Group a section's lines into pieces of at most max_words.

    Splits only between lines, never inside one; a single line longer than max_words
    stays whole. Every piece starts with the section's heading line, so it reads on its own.
    """
    heading = lines[:1] if HEADING.match(lines[0]) else []
    pieces: list[list[str]] = []
    current: list[str] = []
    for line in lines[len(heading):]:
        if current and count_words(heading + current + [line]) > max_words:
            pieces.append(current)
            current = []
        current.append(line)
    pieces.append(current)
    return ["\n".join(heading + piece).strip() for piece in pieces if has_body(piece)]


def has_body(lines: list[str]) -> bool:
    """True if any line is real text (not blank and not a heading)."""
    return any(line.strip() and not HEADING.match(line) for line in lines)


def count_words(lines: list[str]) -> int:
    return sum(len(line.split()) for line in lines)
