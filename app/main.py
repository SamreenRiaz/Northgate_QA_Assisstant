"""The FastAPI application.  Run: uvicorn app.main:app --reload"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import routes_ask, routes_documents
from app.config import FRONTEND_DIR, PROCESSED_DIR
from app.generation.answerer import Answerer
from app.generation.llm import OpenAICompatibleLLM
from app.ingestion.pipeline import read_documents
from app.retrieval.embedder import BgeEmbedder
from app.retrieval.retriever import HybridRetriever
from app.retrieval.vector_store import VectorStore

DOCUMENTS_PATH = PROCESSED_DIR / "documents.jsonl"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load the model, index and documents once, when the server starts."""
    store = VectorStore(BgeEmbedder())
    if store.count() == 0 or not DOCUMENTS_PATH.exists():
        raise RuntimeError("The index is not built. Run: python -m scripts.ingest")
    app.state.answerer = Answerer(HybridRetriever(store), OpenAICompatibleLLM())
    app.state.documents = {document.doc_id: document for document in read_documents(DOCUMENTS_PATH)}
    yield


app = FastAPI(title="Northgate Handbook Assistant", lifespan=lifespan)
app.include_router(routes_ask.router)
app.include_router(routes_documents.router)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")  # after the API routes
