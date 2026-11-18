"""Hybrid retrieval: vector search + BM25 keyword search, combined with Reciprocal Rank Fusion.

Outdated documents (status "deprecated", or replaced by a newer version via "supersedes")
are removed before ranking, because the handbook says they must not be followed.
"""
from app.ingestion.models import Chunk
from app.retrieval.keyword_search import KeywordIndex
from app.retrieval.models import SearchResult
from app.retrieval.vector_store import VectorStore

CANDIDATES = 20  # results taken from EACH search method before fusing
RRF_K = 60  # standard RRF constant (Cormack et al., 2009)


class HybridRetriever:
    def __init__(self, vector_store: VectorStore) -> None:
        chunks = vector_store.get_all_chunks()  # BM25 is built from exactly what Chroma holds
        self._vector_store = vector_store
        self._keyword_index = KeywordIndex(chunks)
        self._outdated = outdated_doc_ids(chunks)

    def search(self, question: str, k: int = 5) -> list[SearchResult]:
        """Top-k chunks for the question, best first. Outdated documents never appear."""
        ranked_lists = [
            self._vector_store.search(question, k=CANDIDATES),
            self._keyword_index.search(question, k=CANDIDATES),
        ]
        allowed_lists = [self._drop_outdated(results) for results in ranked_lists]
        return reciprocal_rank_fusion(allowed_lists)[:k]

    def _drop_outdated(self, results: list[SearchResult]) -> list[SearchResult]:
        return [result for result in results if result.chunk.doc_id not in self._outdated]


def outdated_doc_ids(chunks: list[Chunk]) -> set[str]:
    """Documents that must not be used: status "deprecated", or named in another doc's "supersedes"."""
    deprecated = {chunk.doc_id for chunk in chunks if chunk.metadata.get("status") == "deprecated"}
    superseded = {chunk.metadata["supersedes"] for chunk in chunks if chunk.metadata.get("supersedes")}
    return deprecated | superseded


def reciprocal_rank_fusion(ranked_lists: list[list[SearchResult]], rrf_k: int = RRF_K) -> list[SearchResult]:
    """Combine ranked lists by position only: score = sum over lists of 1 / (rrf_k + rank).

    A chunk ranked well in several lists beats one ranked well in only one. Rank starts at 1.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for results in ranked_lists:
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (rrf_k + rank)
            chunks[chunk_id] = result.chunk
    best_first = sorted(scores, key=scores.get, reverse=True)
    return [SearchResult(chunk=chunks[chunk_id], score=scores[chunk_id]) for chunk_id in best_first]
