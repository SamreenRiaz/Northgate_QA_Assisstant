"""Load the handbook manifest and check it matches the files on disk."""
import json
from pathlib import Path

from app.config import MANIFEST_PATH

REQUIRED_FIELDS = ("doc_id", "path", "title", "category", "owner", "effective_date", "status")


class ManifestError(Exception):
    """Raised when the manifest is broken or does not match the files."""


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> list[dict]:
    """Read manifest.json, check it, and return the list of document entries."""
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    entries = data["documents"]
    validate_manifest(entries, raw_dir=manifest_path.parent)
    return entries


def validate_manifest(entries: list[dict], raw_dir: Path) -> None:
    """Raise ManifestError if anything is missing, duplicated, or unlisted."""
    seen_ids = set()
    for entry in entries:
        missing = [name for name in REQUIRED_FIELDS if name not in entry]
        if missing:
            raise ManifestError(f"{entry.get('doc_id', '?')}: missing fields {missing}")
        if entry["doc_id"] in seen_ids:
            raise ManifestError(f"duplicate doc_id: {entry['doc_id']}")
        seen_ids.add(entry["doc_id"])
        if not (raw_dir / entry["path"]).is_file():
            raise ManifestError(f"{entry['doc_id']}: file not found: {entry['path']}")

    # Checked in a second loop: a newer version may be listed before the one it replaces.
    for entry in entries:
        target = entry.get("supersedes")
        if target and target not in seen_ids:
            raise ManifestError(f"{entry['doc_id']}: supersedes unknown doc_id {target}")

    listed = {entry["path"] for entry in entries}
    on_disk = {
        p.name
        for p in raw_dir.iterdir()
        if p.is_file() and p.name != "manifest.json" and not p.name.startswith(".")
    }
    unlisted = on_disk - listed
    if unlisted:
        raise ManifestError(f"files not in manifest: {sorted(unlisted)}")

