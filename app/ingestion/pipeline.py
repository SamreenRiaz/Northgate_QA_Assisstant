"""Turn the raw handbook files into clean Document objects."""
import json
from dataclasses import asdict
from pathlib import Path

from app.config import MANIFEST_PATH
from app.ingestion.cleaning import clean_text
from app.ingestion.manifest import load_manifest
from app.ingestion.models import Document
from app.ingestion.parsers import parse_file


def load_documents(manifest_path: Path = MANIFEST_PATH) -> list[Document]:
    """manifest -> parse -> clean -> add title if missing -> Document."""
    raw_dir = manifest_path.parent
    documents = []
    for entry in load_manifest(manifest_path):
        text = clean_text(parse_file(raw_dir / entry["path"]))
        if not text.startswith("# "):
            text = f"# {entry['title']}\n\n{text}"
        metadata = {key: value for key, value in entry.items() if key not in ("doc_id", "title")}
        documents.append(Document(doc_id=entry["doc_id"], title=entry["title"], text=text, metadata=metadata))
    return documents


def save_jsonl(items: list, path: Path) -> None:
    """Write dataclass objects to a JSON Lines file (one object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
