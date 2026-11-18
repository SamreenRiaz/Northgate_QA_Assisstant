"""Tests for the ChromaDB vector store (FakeEmbedder, except the one slow test)."""
import pytest

from app.ingestion.chunking import chunk_documents
from app.ingestion.models import Chunk
from app.ingestion.pipeline import load_documents
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.vector_store import VectorStore


def make_chunk(chunk_id, text, status="current", section="Doc > Section"):
    doc_id = chunk_id.split("#")[0]
    return Chunk(chunk_id=chunk_id, doc_id=doc_id, text=text, section=section,
                 metadata={"title": doc_id.title(), "status": status})


CHUNKS = [
    make_chunk("travel#0", "Hotel room rates are capped per night at $275 in tier 1 cities."),
    make_chunk("vpn#0", "You may hold at most two concurrent VPN sessions on company laptops."),
    make_chunk("deploy-2023#0", "A deploy freeze starts 36 hours before every release.", status="deprecated"),
    make_chunk("deploy#0", "A deploy freeze starts 72 hours before every release."),
]


@pytest.fixture
def store(tmp_path, fake_embedder):
    store = VectorStore(fake_embedder, path=tmp_path / "index")
    store.add_chunks(CHUNKS)
    return store


def test_add_and_count(store):
    assert store.count() == 4


def test_search_returns_closest_chunk_first(store):
    results = store.search("hotel room rates per night", k=2)
    assert results[0].chunk.chunk_id == "travel#0"
    assert results[0].score > results[1].score


def test_search_returns_chunk_unchanged(store):
    [result] = store.search("concurrent VPN sessions", k=1)
    assert result.chunk == CHUNKS[1]  # same id, doc_id, text, section and metadata


def test_where_filter_on_metadata(store):
    results = store.search("deploy freeze hours before release", k=4, where={"status": "current"})
    ids = [result.chunk.chunk_id for result in results]
    assert "deploy-2023#0" not in ids
    assert ids[0] == "deploy#0"


def test_k_larger_than_index(store):
    assert len(store.search("anything", k=50)) == 4


def test_re_adding_does_not_duplicate(store):
    store.add_chunks(CHUNKS)
    assert store.count() == 4


def test_reset_empties_the_index(store):
    store.reset()
    assert store.count() == 0
    assert store.search("hotel") == []


def test_index_persists_on_disk(tmp_path, fake_embedder):
    VectorStore(fake_embedder, path=tmp_path / "index").add_chunks(CHUNKS)
    reopened = VectorStore(fake_embedder, path=tmp_path / "index")  # a fresh object, same folder
    assert reopened.count() == 4


@pytest.mark.slow
def test_real_index_finds_hotel_rates(tmp_path):
    """Real model + real chunks: a hotel question must find section 4.2 of the travel policy."""
    store = VectorStore(BgeEmbedder(), path=tmp_path / "index")
    store.add_chunks(chunk_documents(load_documents()))
    top_ids = [result.chunk.chunk_id for result in store.search("What is the max hotel rate in Boston?", k=3)]
    assert "hr-travel-policy#4" in top_ids
