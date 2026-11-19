"""Tests for the answer evaluation's grading and cache: no model, no tokens."""
from app.generation.answerer import Answer, Citation
from app.ingestion.models import Chunk
from eval.run_answer_eval import CachingLLM, contains, grade, is_refusal, normalize

ANSWERABLE = {
    "answerable": True,
    "expected_docs": ["eng-deploy-runbook"],
    "must_contain": ["72"],
    "must_not_contain": ["36"],
}
UNANSWERABLE = {"answerable": False, "expected_docs": [], "must_contain": [], "must_not_contain": []}


def make_answer(text, *cited_doc_ids):
    citations = [Citation(n, Chunk(chunk_id=f"{d}#0", doc_id=d, text="", section="")) for n, d in enumerate(cited_doc_ids, 1)]
    return Answer(text=text, citations=citations)


# --- Normalizing and matching ---------------------------------------------------


def test_normalize_lookalike_hyphens_bold_and_case():
    assert normalize("**Effective** 2027‑01‑01") == "effective 2027-01-01"


def test_contains_alternatives():
    assert contains("Up to two sessions.", "2|two")
    assert not contains("Up to three sessions.", "2|two")


def test_is_refusal():
    assert is_refusal("The handbook does not cover this.")
    assert not is_refusal("The freeze starts 72 hours before [1].")


# --- Grading --------------------------------------------------------------------


def test_grade_pass():
    result = grade(ANSWERABLE, make_answer("The freeze starts 72 hours before [1].", "eng-deploy-runbook"))
    assert result == {"facts_ok": True, "citations_ok": True, "refusal_ok": True, "passed": True}


def test_grade_forbidden_fact_fails():
    result = grade(ANSWERABLE, make_answer("72 hours now, 36 hours before [1].", "eng-deploy-runbook"))
    assert result["facts_ok"] is False and result["passed"] is False


def test_grade_wrong_citation_fails():
    result = grade(ANSWERABLE, make_answer("72 hours [1].", "notes-allhands-2026-09"))
    assert result["citations_ok"] is False and result["passed"] is False


def test_grade_answerable_refused_fails():
    result = grade(ANSWERABLE, make_answer("The handbook does not cover this."))
    assert result["refusal_ok"] is False and result["passed"] is False


def test_grade_unanswerable():
    assert grade(UNANSWERABLE, make_answer("The handbook does not cover this."))["passed"] is True
    assert grade(UNANSWERABLE, make_answer("The CEO is Tyler Anderson [1].", "org-chart"))["passed"] is False


# --- Cache ----------------------------------------------------------------------

MESSAGES = [{"role": "user", "content": "How long is the freeze?"}]


def test_cache_reuses_saved_answer(tmp_path, fake_llm):
    cache = CachingLLM(fake_llm, model="m", path=tmp_path / "cache.json")
    assert cache.complete(MESSAGES) == cache.complete(MESSAGES)
    assert len(fake_llm.calls) == 1 and cache.new_calls == 1


def test_cache_survives_restart(tmp_path, fake_llm):
    CachingLLM(fake_llm, model="m", path=tmp_path / "cache.json").complete(MESSAGES)
    restarted = CachingLLM(fake_llm, model="m", path=tmp_path / "cache.json")
    restarted.complete(MESSAGES)
    assert len(fake_llm.calls) == 1 and restarted.new_calls == 0


def test_cache_changed_prompt_or_model_asks_again(tmp_path, fake_llm):
    cache = CachingLLM(fake_llm, model="m", path=tmp_path / "cache.json")
    cache.complete(MESSAGES)
    cache.complete([{"role": "user", "content": "A different prompt"}])
    CachingLLM(fake_llm, model="other-model", path=tmp_path / "cache.json").complete(MESSAGES)
    assert len(fake_llm.calls) == 3
