"""Project settings: where the data lives, which models we use.
"""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# The project root is the folder that contains app/.
# __file__ is this file (app/config.py); .parent is app/; .parent again is the root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # original handbook files (read-only)
MANIFEST_PATH = RAW_DIR / "manifest.json"
PROCESSED_DIR = DATA_DIR / "processed"  # generated: documents.jsonl, chunks.jsonl
MODELS_DIR = DATA_DIR / "models"  # downloaded embedding model files 
INDEX_DIR = DATA_DIR / "index"  # ChromaDB vector index, rebuilt by the ingest script 
USAGE_LOG_PATH = DATA_DIR / "logs" / "llm_usage.jsonl"  # tokens used per LLM call 

# Embedding model, run locally with fastembed (ONNX Runtime, no API key, no data leaves the machine).
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Language model, reached through any OpenAI-compatible API (Groq by default).
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")  # empty for models without reasoning
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))  # cap per answer, reasoning included


def today() -> date:
    """Today's date, or the fixed TODAY from .env so evaluation runs are repeatable."""
    fixed = os.getenv("TODAY")
    return date.fromisoformat(fixed) if fixed else date.today()
