"""Store chunk vectors in ChromaDB and find the chunks closest to a question.

We always compute vectors ourselves with an Embedder and hand them to Chroma, so
Chroma never picks its own embedding model.
"""
from pathlib import Path

import chromadb
from chromadb.config import Settings

from app.config import INDEX_DIR
from app.ingestion.models import Chunk
from app.retrieval.embedder import Embedder
from app.retrieval.models import SearchResult

COLLECTION_NAME = "handbook_chunks"


class VectorStore:
    def __init__(self, embedder: Embedder, path: Path = INDEX_DIR) -> None:
        self._embedder = embedder
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=Settings(anonymized_telemetry=False),  # no usage data sent to Chroma
        )
        self._collection = self._open_collection()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Embed chunks and store them. Re-adding a chunk_id replaces it (no duplicates)."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=self._embedder.embed_documents([chunk.text for chunk in chunks]),
            documents=[chunk.text for chunk in chunks],
            metadatas=[to_chroma_metadata(chunk) for chunk in chunks],
        )

    def search(self, question: str, k: int = 5, where: dict | None = None) -> list[SearchResult]:
        """Return up to k chunks closest in meaning to the question, best first.

        Score is cosine similarity (closer to 1 = closer in meaning).
        `where` filters on metadata before ranking, e.g. {"status": "current"}.
        """
        if self.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[self._embedder.embed_query(question)],
            n_results=min(k, self.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        # Chroma returns one list per question; we asked one question, so take [0].
        rows = zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])
        return [
            SearchResult(chunk=from_chroma_metadata(chunk_id, text, metadata), score=1 - distance)
            for chunk_id, text, metadata, distance in rows
        ]

    def get_all_chunks(self) -> list[Chunk]:
        """Every stored chunk, e.g. to build the keyword index from the same data."""
        result = self._collection.get(include=["documents", "metadatas"])
        rows = zip(result["ids"], result["documents"], result["metadatas"])
        return [from_chroma_metadata(chunk_id, text, metadata) for chunk_id, text, metadata in rows]

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Delete everything, e.g. before rebuilding the index from scratch."""
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._open_collection()

    def _open_collection(self):
        return self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # compare vectors by angle (cosine distance)
            embedding_function=None,  # we always pass our own vectors
        )


def to_chroma_metadata(chunk: Chunk) -> dict:
    """Chroma keeps one flat metadata dict per entry, so doc_id and section go in it too."""
    return {**chunk.metadata, "doc_id": chunk.doc_id, "section": chunk.section}


def from_chroma_metadata(chunk_id: str, text: str, metadata: dict) -> Chunk:
    """Rebuild the original Chunk from what Chroma returns."""
    metadata = dict(metadata)
    doc_id = metadata.pop("doc_id")
    section = metadata.pop("section")
    return Chunk(chunk_id=chunk_id, doc_id=doc_id, text=text, section=section, metadata=metadata)
