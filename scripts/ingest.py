"""Build documents.jsonl and chunks.jsonl in data/processed/.  Run: python -m scripts.ingest"""
from app.config import PROCESSED_DIR
from app.ingestion.chunking import chunk_documents
from app.ingestion.pipeline import load_documents, save_jsonl


def main() -> None:
    documents = load_documents()
    chunks = chunk_documents(documents)
    save_jsonl(documents, PROCESSED_DIR / "documents.jsonl")
    save_jsonl(chunks, PROCESSED_DIR / "chunks.jsonl")
    print(f"Wrote {len(documents)} documents and {len(chunks)} chunks to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
