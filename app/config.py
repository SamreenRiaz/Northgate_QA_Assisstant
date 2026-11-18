"""Project settings: where the data lives."""
from pathlib import Path

# The project root is the folder that contains app/.
# __file__ is this file (app/config.py); .parent is app/; .parent again is the root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # original handbook files (read-only)
MANIFEST_PATH = RAW_DIR / "manifest.json"
PROCESSED_DIR = DATA_DIR / "processed"  # generated: documents.jsonl, chunks.jsonl (gitignored)
