"""Tests for the retrieval evaluation's scoring functions, and for the question set itself."""
import json

import pytest

from app.ingestion.manifest import load_manifest
from eval.run_retrieval_eval import QUESTIONS_PATH, first_hit_rank, score_question, summarize


def test_first_hit_rank():
    assert first_hit_rank(["a", "b", "c"], {"b", "c"}) == 2
    assert first_hit_rank(["a", "a"], {"z"}) is None


def test_score_question_hit_and_leak():
    scores = score_question(["old", "b"], expected_docs={"b"}, outdated={"old"})
    assert scores == {"rank": 2, "hit1": False, "hit5": True, "reciprocal_rank": 0.5, "leak": True}


def test_score_question_miss():
    scores = score_question(["a"], expected_docs={"z"}, outdated=set())
    assert scores["hit5"] is False and scores["reciprocal_rank"] == 0.0 and scores["leak"] is False


def test_summarize():
    rows = [
        score_question(["b"], {"b"}, set()),  # rank 1
        score_question(["a", "b"], {"b"}, set()),  # rank 2
        score_question(["a"], {"b"}, {"a"}),  # miss + leak
    ]
    summary = summarize(rows)
    assert summary["questions"] == 3
    assert summary["hit1"] == pytest.approx(1 / 3)
    assert summary["hit5"] == pytest.approx(2 / 3)
    assert summary["mrr"] == pytest.approx((1 + 0.5 + 0) / 3)
    assert summary["leaks"] == 1


def test_question_set_is_valid():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    doc_ids = {entry["doc_id"] for entry in load_manifest()}
    assert len({q["id"] for q in questions}) == len(questions)  # ids unique
    for q in questions:
        assert set(q["expected_docs"]) <= doc_ids, q["id"]
        assert bool(q["expected_docs"]) == q["answerable"], q["id"]
