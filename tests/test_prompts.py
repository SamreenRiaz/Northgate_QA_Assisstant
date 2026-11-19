"""Tests for prompt building."""
from datetime import date

from app.generation.prompts import NOT_COVERED, build_messages, format_passage
from app.ingestion.models import Chunk
from app.retrieval.models import SearchResult

TODAY = date(2026, 11, 19)


def make_chunk(effective_date="2024-06-01", category="HR", section="Travel Policy > 4.2 Hotels", text="Tier 1: $275."):
    return Chunk(chunk_id="doc#0", doc_id="doc", text=text, section=section,
                 metadata={"effective_date": effective_date, "category": category, "title": "Doc"})


def test_system_message_has_rules_and_today():
    system, _ = build_messages("q", [], TODAY)
    assert system["role"] == "system"
    assert "Today is 2026-11-19." in system["content"]
    assert NOT_COVERED in system["content"]


def test_user_message_has_numbered_passages_and_question():
    results = [SearchResult(make_chunk(text="First."), 0.9), SearchResult(make_chunk(text="Second."), 0.8)]
    _, user = build_messages("What is the hotel cap?", results, TODAY)
    assert user["role"] == "user"
    assert "[1] Travel Policy > 4.2 Hotels (effective 2024-06-01)\nFirst." in user["content"]
    assert "[2] " in user["content"] and "Second." in user["content"]
    assert user["content"].endswith("Question: What is the hotel cap?")


def test_future_passage_marked_not_in_effect():
    header = format_passage(1, make_chunk(effective_date="2027-01-01"), TODAY).splitlines()[0]
    assert "NOT YET IN EFFECT until 2027-01-01" in header


def test_current_passage_not_marked():
    assert "NOT YET IN EFFECT" not in format_passage(1, make_chunk(effective_date="2026-11-19"), TODAY)


def test_meeting_notes_marked():
    header = format_passage(1, make_chunk(category="Meeting Notes"), TODAY).splitlines()[0]
    assert "meeting notes" in header
