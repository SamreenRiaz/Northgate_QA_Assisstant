"""Tests for the HTTP API, with fakes in place of the model, index and LLM: no network, no tokens.

TestClient is used without "with", so the startup step (loading the real model and index)
does not run; the routes get their objects from dependency overrides instead.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_answerer, get_documents
from app.config import RAW_DIR
from app.generation.answerer import Answerer
from app.generation.llm import LLMError
from app.ingestion.models import Chunk, Document
from app.main import app
from app.retrieval.models import SearchResult
from tests.fakes import FakeLLM, FakeRetriever

VPN_METADATA = {"title": "VPN Guide", "path": "it-vpn-guide.md", "category": "IT",
                "owner": "IT Operations", "effective_date": "2024-08-20", "status": "current"}
FUTURE_METADATA = {"title": "Parental Leave Policy (2027 revision)", "category": "HR", "effective_date": "2027-01-01"}

RESULTS = [
    SearchResult(Chunk("it-vpn-guide#0", "it-vpn-guide", "At most 2 sessions.", "VPN Guide", VPN_METADATA), 0.9),
    SearchResult(Chunk("parental-2027#0", "parental-2027", "26 weeks from 2027.", "Parental 2027", FUTURE_METADATA), 0.8),
]
DOCUMENTS = {"it-vpn-guide": Document("it-vpn-guide", "VPN Guide", "# VPN Guide\nAt most 2 sessions.", VPN_METADATA)}


class FailingLLM:
    def complete(self, messages):
        raise LLMError("Rate limit reached for test-model (it may be the daily limit)")


@pytest.fixture
def client():
    llm = FakeLLM(reply="You may hold 2 VPN sessions [1]; a change comes in 2027 [2].")
    app.dependency_overrides[get_answerer] = lambda: Answerer(FakeRetriever(RESULTS), llm)
    app.dependency_overrides[get_documents] = lambda: DOCUMENTS
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- POST /api/ask --------------------------------------------------------------


def test_ask_returns_answer_and_citations(client, monkeypatch):
    monkeypatch.setenv("TODAY", "2026-11-19")
    response = client.post("/api/ask", json={"question": "How many VPN sessions can I have?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You may hold 2 VPN sessions [1]; a change comes in 2027 [2]."
    assert body["citations"][0] == {
        "number": 1,
        "doc_id": "it-vpn-guide",
        "title": "VPN Guide",
        "section": "VPN Guide",
        "text": "At most 2 sessions.",
        "effective_date": "2024-08-20",
        "labels": [],
    }
    assert body["citations"][1]["labels"] == ["NOT YET IN EFFECT until 2027-01-01"]


@pytest.mark.parametrize("payload", [{"question": "   "}, {"question": "x" * 501}, {}])
def test_ask_rejects_invalid_question(client, payload):
    assert client.post("/api/ask", json=payload).status_code == 422


def test_ask_llm_failure_returns_503(client):
    app.dependency_overrides[get_answerer] = lambda: Answerer(FakeRetriever(RESULTS), FailingLLM())
    response = client.post("/api/ask", json={"question": "Anything?"})
    assert response.status_code == 503
    assert "Rate limit reached" in response.json()["detail"]


# --- GET /api/documents/{doc_id} --------------------------------------------------


def test_get_document(client):
    response = client.get("/api/documents/it-vpn-guide")
    assert response.status_code == 200
    assert response.json() == {"doc_id": "it-vpn-guide", "title": "VPN Guide",
                               "text": "# VPN Guide\nAt most 2 sessions.", "metadata": VPN_METADATA}


def test_get_document_file_returns_original(client):
    response = client.get("/api/documents/it-vpn-guide/file")
    assert response.status_code == 200
    assert response.content == (RAW_DIR / "it-vpn-guide.md").read_bytes()


@pytest.mark.parametrize("url", ["/api/documents/no-such-doc", "/api/documents/no-such-doc/file"])
def test_unknown_document_returns_404(client, url):
    assert client.get(url).status_code == 404


# --- GET / (web page) -----------------------------------------------------------------


def test_web_page_and_assets_served(client):
    page = client.get("/")
    assert page.status_code == 200 and "Handbook Assistant" in page.text
    assert client.get("/css/styles.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200
