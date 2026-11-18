"""Tests for the ingestion pipeline (manifest -> parse -> clean -> Document)."""
import json

import pytest

from app.ingestion.models import Document
from app.ingestion.pipeline import load_documents, save_jsonl


@pytest.fixture(scope="module")
def documents_by_id():
    """Run the real pipeline once and share the result between tests in this file."""
    return {doc.doc_id: doc for doc in load_documents()}


def test_load_documents_real_data(documents_by_id):
    assert len(documents_by_id) == 64
    for doc in documents_by_id.values():
        assert doc.text.startswith("# "), doc.doc_id
        assert len(doc.text) > 20, doc.doc_id


def test_title_added_when_missing(documents_by_id):
    text = documents_by_id["fin-per-diem-table"].text
    assert text.startswith("# Per-Diem Table\n\n- grade: L1")


def test_existing_title_kept(documents_by_id):
    doc = documents_by_id["notes-allhands-2026-09"]
    assert doc.text.startswith("# All-hands summary, September 25, 2026")
    assert doc.title == "All-Hands Summary, September 2026"  # title field comes from the manifest


def test_metadata_from_manifest(documents_by_id):
    metadata = documents_by_id["hr-leave-policy-v2"].metadata
    assert metadata["status"] == "current"
    assert metadata["supersedes"] == "hr-leave-policy-v1"
    assert metadata["path"] == "hr-leave-policy-v2.pdf"
    assert "doc_id" not in metadata and "title" not in metadata


def test_save_jsonl_round_trip(tmp_path):
    docs = [
        Document(doc_id="a", title="A", text="# A\n\nText a", metadata={"status": "current"}),
        Document(doc_id="b", title="B", text="# B\n\nText b"),
    ]
    path = tmp_path / "out" / "documents.jsonl"  # "out" does not exist yet: save_jsonl creates it
    save_jsonl(docs, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [Document(**json.loads(line)) for line in lines] == docs
