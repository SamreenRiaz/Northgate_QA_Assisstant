"""Objects the routes need, created once at startup (see app.main) and replaceable in tests."""
from fastapi import Request

from app.generation.answerer import Answerer
from app.ingestion.models import Document


def get_answerer(request: Request) -> Answerer:
    return request.app.state.answerer


def get_documents(request: Request) -> dict[str, Document]:
    return request.app.state.documents
