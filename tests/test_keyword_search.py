"""Tests for BM25 keyword search."""
import pytest

from app.ingestion.chunking import chunk_documents
from app.ingestion.models import Chunk
from app.ingestion.pipeline import load_documents
from app.retrieval.keyword_search import KeywordIndex, tokenize


def make_chunk(chunk_id, text, section="Doc"):
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], text=text, section=section)


CHUNKS = [
    make_chunk("booking#0", "Book all flights and hotels through VoyageHub.", section="Travel Policy > Booking"),
    make_chunk("hotels#0", "Room rates are capped per night by city tier.", section="Travel Policy > Accommodation"),
    make_chunk("vpn#0", "You may hold at most two concurrent VPN sessions."),
    make_chunk("leave#0", "Employees receive eight days of sick leave per year."),
]


@pytest.fixture
def index():
    return KeywordIndex(CHUNKS)


def test_tokenize():
    assert tokenize("Tier 1: $275, see 4.2 (VoyageHub)") == ["tier", "1", "275", "see", "4.2", "voyagehub"]


def test_tokenize_splits_hyphens():
    assert tokenize("on-call per-diem") == ["on", "call", "per", "diem"]


def test_exact_rare_word_wins(index):
    results = index.search("How do I use VoyageHub?")
    assert results[0].chunk.chunk_id == "booking#0"


def test_case_and_punctuation_ignored(index):
    assert index.search("voyagehub?")[0].chunk.chunk_id == index.search("VoyageHub")[0].chunk.chunk_id


def test_section_words_count(index):
    # "accommodation" appears only in the section path of hotels#0, never in any text.
    assert index.search("accommodation")[0].chunk.chunk_id == "hotels#0"


def test_no_shared_words_returns_empty(index):
    assert index.search("quarterly revenue forecast") == []


def test_results_sorted_and_limited(index):
    results = index.search("travel policy hotels VoyageHub", k=2)
    assert len(results) <= 2
    assert results == sorted(results, key=lambda result: result.score, reverse=True)


def test_empty_index():
    assert KeywordIndex([]).search("anything") == []


@pytest.mark.parametrize(
    "question, expected_doc",
    [
        ("When is release 2026.22?", "eng-release-calendar"),
        ("SEV2 acknowledge time", "eng-sev-definitions"),
        ("incident phone bridge extension 304", "eng-oncall-runbook"),
    ],
)
def test_real_codes_and_numbers(question, expected_doc):
    index = KeywordIndex(chunk_documents(load_documents()))
    assert index.search(question, k=3)[0].chunk.doc_id == expected_doc
