"""Build documents.jsonl, chunks.jsonl and the vector index.  Run: python -m scripts.ingest"""
from app.config import INDEX_DIR, PROCESSED_DIR
from app.ingestion.chunking import chunk_documents
from app.ingestion.pipeline import load_documents, save_jsonl
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.vector_store import VectorStore


def main() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    save_jsonl(documents, PROCESSED_DIR / "documents.jsonl")
    save_jsonl(chunks, PROCESSED_DIR / "chunks.jsonl")
    print(f"Wrote {len(documents)} documents and {len(chunks)} chunks to {PROCESSED_DIR}")

    store = VectorStore(BgeEmbedder())
    store.reset()  # rebuild from scratch, so removed or renamed chunks do not linger
    store.add_chunks(chunks)
    print(f"Indexed {store.count()} chunks in {INDEX_DIR}")


if __name__ == "__main__":
    main()
