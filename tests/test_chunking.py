"""Tests for heading-based chunking."""
import pytest

from app.ingestion.chunking import MAX_WORDS, chunk_document, chunk_documents, pack_lines
from app.ingestion.models import Document
from app.ingestion.pipeline import load_documents

TRAVEL_TEXT = """# Travel Policy
## 1. Scope
Applies to all travel.
## 4. Limits
### 4.1 Flights
Economy class only.
### 4.2 Hotels
Tier 1: $275.
## 5. Insurance
Included automatically."""


def make_doc(text, doc_id="doc", **metadata):
    return Document(doc_id=doc_id, title="Doc Title", text=text, metadata=metadata)


@pytest.fixture(scope="module")
def real_chunks():
    """Chunk the real handbook once and share the result between tests in this file."""
    return chunk_documents(load_documents())


# --- Splitting and section paths ----------------------------------------------


def test_splits_at_every_heading_level():
    chunks = chunk_document(make_doc(TRAVEL_TEXT))
    assert [chunk.text.splitlines()[0] for chunk in chunks] == [
        "## 1. Scope",
        "### 4.1 Flights",
        "### 4.2 Hotels",
        "## 5. Insurance",
    ]


def test_section_path():
    chunks = chunk_document(make_doc(TRAVEL_TEXT))
    assert [chunk.section for chunk in chunks] == [
        "Travel Policy > 1. Scope",
        "Travel Policy > 4. Limits > 4.1 Flights",
        "Travel Policy > 4. Limits > 4.2 Hotels",
        "Travel Policy > 5. Insurance",  # "4. Limits" dropped out of the path
    ]


def test_heading_without_body_is_not_a_chunk():
    texts = [chunk.text for chunk in chunk_document(make_doc(TRAVEL_TEXT))]
    assert not any(text.startswith("# Travel Policy") for text in texts)
    assert not any(text.startswith("## 4. Limits") for text in texts)


def test_title_only_document_is_one_chunk():
    chunks = chunk_document(make_doc("# Glossary\n\nAPI: application interface.\nSLA: service level."))
    assert len(chunks) == 1
    assert chunks[0].section == "Glossary"
    assert chunks[0].text.startswith("# Glossary")


def test_hash_inside_line_is_not_heading():
    chunks = chunk_document(make_doc("# Runbook\nPost the summary in #deploys.\n#notaheading either"))
    assert len(chunks) == 1
    assert "Post the summary in #deploys." in chunks[0].text
    assert "#notaheading either" in chunks[0].text


# --- Size limit ---------------------------------------------------------------


def test_long_section_split_between_lines():
    body = [f"line{i} " + " ".join(["word"] * 9) for i in range(30)]  # 30 lines x 10 words
    pieces = pack_lines(["## Big"] + body, max_words=200)
    assert len(pieces) == 2
    for piece in pieces:
        assert piece.startswith("## Big\n")
        assert len(piece.split()) <= 200
    kept_lines = [line for piece in pieces for line in piece.splitlines()[1:]]
    assert kept_lines == body  # nothing lost, nothing cut, order kept


def test_single_long_line_kept_whole():
    long_line = "word " * 300
    pieces = pack_lines(["## Big", long_line], max_words=200)
    assert len(pieces) == 1
    assert len(pieces[0].split()) == 302  # heading (2 words) + 300


# --- Chunk ids and metadata ---------------------------------------------------


def test_chunk_ids_and_metadata():
    doc = make_doc(TRAVEL_TEXT, doc_id="hr-travel", status="current")
    chunks = chunk_document(doc)
    assert [chunk.chunk_id for chunk in chunks] == ["hr-travel#0", "hr-travel#1", "hr-travel#2", "hr-travel#3"]
    assert all(chunk.doc_id == "hr-travel" for chunk in chunks)
    assert chunks[0].metadata == {"title": "Doc Title", "status": "current"}


def test_chunk_metadata_is_independent():
    doc = make_doc(TRAVEL_TEXT, status="current")
    chunks = chunk_document(doc)
    chunks[0].metadata["status"] = "changed"
    assert chunks[1].metadata["status"] == "current"
    assert doc.metadata["status"] == "current"


# --- Real handbook ------------------------------------------------------------


def test_real_travel_hotel_chunk(real_chunks):
    hotel = [c for c in real_chunks if c.section == "Travel Policy > 4. Limits > 4.2 Hotels and daily spending limits"]
    assert len(hotel) == 1
    for rate in ("$275", "$200", "$150"):
        assert rate in hotel[0].text


def test_real_corpus_chunk_sizes(real_chunks):
    for chunk in real_chunks:
        body_lines = [line for line in chunk.text.splitlines()[1:] if line.strip()]
        assert len(chunk.text.split()) <= MAX_WORDS or len(body_lines) == 1, chunk.chunk_id


def test_real_corpus_every_document_has_chunks(real_chunks):
    assert {chunk.doc_id for chunk in real_chunks} == {doc.doc_id for doc in load_documents()}
    assert len({chunk.chunk_id for chunk in real_chunks}) == len(real_chunks)  # ids unique
