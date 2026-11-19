"""Tests for the answerer, with a fake retriever and the FakeLLM: no model, no tokens."""
from app.generation.answerer import Answerer, cited_passages
from app.ingestion.models import Chunk
from app.retrieval.models import SearchResult


def make_result(chunk_id, text):
    chunk = Chunk(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], text=text, section="S",
                  metadata={"effective_date": "2025-01-01", "category": "HR", "title": "T"})
    return SearchResult(chunk=chunk, score=0.5)


RESULTS = [
    make_result("leave-v2#1", "Employees accrue 16 days of annual leave."),
    make_result("travel#4", "Tier 1 hotels: $275 per night."),
    make_result("vpn#0", "At most 2 VPN sessions."),
]


class FakeRetriever:
    def __init__(self, results):
        self.results = results
        self.asked = None

    def search(self, question, k):
        self.asked = (question, k)
        return self.results[:k]


def test_answer_uses_retrieved_passages_and_question(fake_llm):
    retriever = FakeRetriever(RESULTS)
    Answerer(retriever, fake_llm, k=3).answer("How much annual leave do I get?")
    assert retriever.asked == ("How much annual leave do I get?", 3)
    user_message = fake_llm.calls[0][1]["content"]
    assert "16 days of annual leave" in user_message and "Question: How much annual leave" in user_message


def test_answer_returns_text_and_cited_sources(fake_llm):
    fake_llm.reply = "You get 16 days per year [1]."
    answer = Answerer(FakeRetriever(RESULTS), fake_llm).answer("Annual leave?")
    assert answer.text == "You get 16 days per year [1]."
    assert [(c.number, c.chunk.chunk_id) for c in answer.citations] == [(1, "leave-v2#1")]


def test_answer_uses_today(fake_llm, monkeypatch):
    monkeypatch.setenv("TODAY", "2026-11-19")
    Answerer(FakeRetriever(RESULTS), fake_llm).answer("q")
    assert "Today is 2026-11-19." in fake_llm.calls[0][0]["content"]


def test_citation_formats_parsed_and_deduplicated():
    cited = cited_passages("A [3][1]. B [1, 2]. C [2].", RESULTS)
    assert [c.number for c in cited] == [1, 2, 3]


def test_citation_out_of_range_ignored():
    assert [c.number for c in cited_passages("See [2] and [7] and [0].", RESULTS)] == [2]


def test_no_citations():
    assert cited_passages("The handbook does not cover this.", RESULTS) == []
