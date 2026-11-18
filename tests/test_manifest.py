"""Tests for loading and validating the manifest."""
import json

import pytest

from app.ingestion.manifest import ManifestError, load_manifest


def make_entry(doc_id, path, **extra):
    """Build one valid manifest entry; extra fields are added or overridden."""
    entry = {
        "doc_id": doc_id,
        "path": path,
        "title": doc_id,
        "category": "HR",
        "owner": "People Operations",
        "effective_date": "2024-01-01",
        "status": "current",
    }
    entry.update(extra)
    return entry


def write_manifest(folder, entries, files):
    """Create the given files and a manifest.json in folder; return the manifest path."""
    for name in files:
        (folder / name).write_text("some text", encoding="utf-8")
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps({"documents": entries}), encoding="utf-8")
    return manifest_path


def test_real_manifest_loads():
    entries = load_manifest()
    assert len(entries) == 64
    doc_ids = {entry["doc_id"] for entry in entries}
    assert "hr-travel-policy" in doc_ids


def test_valid_fake_manifest_loads(tmp_path):
    entries = [make_entry("a", "a.md"), make_entry("b", "b.md", supersedes="a")]
    manifest_path = write_manifest(tmp_path, entries, files=["a.md", "b.md"])
    assert len(load_manifest(manifest_path)) == 2


def test_missing_file_raises(tmp_path):
    manifest_path = write_manifest(tmp_path, [make_entry("a", "a.md")], files=[])
    with pytest.raises(ManifestError, match="file not found"):
        load_manifest(manifest_path)


def test_duplicate_doc_id_raises(tmp_path):
    entries = [make_entry("a", "a.md"), make_entry("a", "b.md")]
    manifest_path = write_manifest(tmp_path, entries, files=["a.md", "b.md"])
    with pytest.raises(ManifestError, match="duplicate doc_id"):
        load_manifest(manifest_path)


def test_unknown_supersedes_raises(tmp_path):
    entries = [make_entry("a", "a.md", supersedes="no-such-doc")]
    manifest_path = write_manifest(tmp_path, entries, files=["a.md"])
    with pytest.raises(ManifestError, match="supersedes unknown"):
        load_manifest(manifest_path)


def test_missing_field_raises(tmp_path):
    entry = make_entry("a", "a.md")
    del entry["status"]
    manifest_path = write_manifest(tmp_path, [entry], files=["a.md"])
    with pytest.raises(ManifestError, match="missing fields"):
        load_manifest(manifest_path)


def test_unlisted_file_raises(tmp_path):
    manifest_path = write_manifest(tmp_path, [make_entry("a", "a.md")], files=["a.md", "extra.md"])
    with pytest.raises(ManifestError, match="files not in manifest"):
        load_manifest(manifest_path)

