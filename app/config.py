"""Project settings: where the data lives."""
from pathlib import Path

# The project root is the folder that contains app/.
# __file__ is this file (app/config.py); .parent is app/; .parent again is the root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # original handbook files (read-only)
MANIFEST_PATH = RAW_DIR / "manifest.json"
PROCESSED_DIR = DATA_DIR / "processed"  # generated: documents.jsonl, chunks.jsonl (gitignored)
MODELS_DIR = DATA_DIR / "models"  # downloaded embedding model files (gitignored)
INDEX_DIR = DATA_DIR / "index"  # ChromaDB vector index, rebuilt by the ingest script (gitignored)

# Embedding model, run locally with fastembed (ONNX Runtime, no API key, no data leaves the machine).
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
