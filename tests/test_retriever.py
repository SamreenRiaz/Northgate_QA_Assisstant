"""Tests for Reciprocal Rank Fusion and the hybrid retriever."""
import math

import pytest

from app.ingestion.chunking import chunk_documents
from app.ingestion.models import Chunk
from app.ingestion.pipeline import load_documents
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.models import SearchResult
from app.retrieval.retriever import HybridRetriever, outdated_doc_ids, reciprocal_rank_fusion
from app.retrieval.vector_store import VectorStore


def make_chunk(chunk_id, text="text", **metadata):
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], text=text, section="S",
                 metadata={"status": "current", **metadata})


def ranked(*chunk_ids):
    """A ranked result list; scores do not matter to RRF, only the order."""
    return [SearchResult(chunk=make_chunk(chunk_id), score=0.0) for chunk_id in chunk_ids]


# --- Reciprocal Rank Fusion -----------------------------------------------------


def test_rrf_chunk_in_both_lists_wins():
    fused = reciprocal_rank_fusion([ranked("a#0", "b#0"), ranked("b#0", "c#0")])
    assert fused[0].chunk.chunk_id == "b#0"  # rank 2 + rank 1 beats rank 1 + absent


def test_rrf_scores_match_formula():
    fused = reciprocal_rank_fusion([ranked("a#0", "b#0"), ranked("b#0")])
    scores = {result.chunk.chunk_id: result.score for result in fused}
    assert math.isclose(scores["b#0"], 1 / 62 + 1 / 61)
    assert math.isclose(scores["a#0"], 1 / 61)


def test_rrf_chunk_in_one_list_still_included():
    fused = reciprocal_rank_fusion([ranked("a#0"), ranked("b#0")])
    assert {result.chunk.chunk_id for result in fused} == {"a#0", "b#0"}


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []


# --- Outdated documents ---------------------------------------------------------


def test_outdated_doc_ids():
    chunks = [
        make_chunk("runbook-2023#0", status="deprecated"),
        make_chunk("runbook#0"),
        make_chunk("leave-v1#0"),  # says "current", but v2 replaces it
        make_chunk("leave-v2#0", supersedes="leave-v1"),
    ]
    assert outdated_doc_ids(chunks) == {"runbook-2023", "leave-v1"}


# --- Hybrid retriever (FakeEmbedder) --------------------------------------------

CHUNKS = [
    make_chunk("runbook-2023#0", "A deploy freeze starts 36 hours before every release.", status="deprecated"),
    make_chunk("runbook#0", "Deploys pause during a freeze window of 72 hours before each release."),
    make_chunk("leave-v1#0", "Employees accrue 12 days of annual leave per year."),
    make_chunk("leave-v2#0", "Employees accrue 16 days of annual leave per year.", supersedes="leave-v1"),
    make_chunk("vpn#0", "You may hold at most two concurrent VPN sessions."),
]


@pytest.fixture
def retriever(tmp_path, fake_embedder):
    store = VectorStore(fake_embedder, path=tmp_path / "index")
    store.add_chunks(CHUNKS)
    return HybridRetriever(store)


def test_deprecated_never_returned(retriever):
    # The deprecated text matches this question best, word for word.
    ids = [result.chunk.chunk_id for result in retriever.search("deploy freeze starts hours before every release")]
    assert "runbook-2023#0" not in ids
    assert ids[0] == "runbook#0"


def test_superseded_never_returned(retriever):
    ids = [result.chunk.chunk_id for result in retriever.search("how many days of annual leave do employees accrue")]
    assert "leave-v1#0" not in ids
    assert ids[0] == "leave-v2#0"


def test_search_respects_k(retriever):
    assert len(retriever.search("employees leave deploy release VPN", k=2)) == 2


def test_get_all_chunks_round_trip(tmp_path, fake_embedder):
    store = VectorStore(fake_embedder, path=tmp_path / "index")
    store.add_chunks(CHUNKS)
    stored = sorted(store.get_all_chunks(), key=lambda chunk: chunk.chunk_id)
    assert stored == sorted(CHUNKS, key=lambda chunk: chunk.chunk_id)


# --- Real handbook (slow) -------------------------------------------------------


@pytest.fixture(scope="module")
def real_retriever(tmp_path_factory):
    store = VectorStore(BgeEmbedder(), path=tmp_path_factory.mktemp("index"))
    store.add_chunks(chunk_documents(load_documents()))
    return HybridRetriever(store)


@pytest.mark.slow
def test_real_freeze_question_ignores_deprecated_runbook(real_retriever):
    results = real_retriever.search("How long before a release does the deploy freeze start?")
    assert all(result.chunk.doc_id != "eng-deploy-runbook-2023" for result in results)
    assert any("72 hours" in result.chunk.text for result in results)


@pytest.mark.slow
def test_real_leave_question_uses_v2_only(real_retriever):
    doc_ids = [result.chunk.doc_id for result in real_retriever.search("How many days of annual leave do I get?")]
    assert "hr-leave-policy-v2" in doc_ids
    assert "hr-leave-policy-v1" not in doc_ids
