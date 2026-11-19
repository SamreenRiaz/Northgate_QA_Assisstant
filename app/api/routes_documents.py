"""GET /api/documents/{doc_id}: a full document, as parsed text or as the original file."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import get_documents
from app.api.schemas import DocumentOut
from app.config import RAW_DIR
from app.ingestion.models import Document

router = APIRouter(prefix="/api/documents")


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, documents: dict[str, Document] = Depends(get_documents)) -> DocumentOut:
    document = find_document(doc_id, documents)
    return DocumentOut(doc_id=document.doc_id, title=document.title, text=document.text, metadata=document.metadata)


@router.get("/{doc_id}/file")
def get_document_file(doc_id: str, documents: dict[str, Document] = Depends(get_documents)) -> FileResponse:
    """The original handbook file. Its path comes from the manifest, never from the request."""
    document = find_document(doc_id, documents)
    path = RAW_DIR / document.metadata["path"]
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


def find_document(doc_id: str, documents: dict[str, Document]) -> Document:
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail=f"No document with id '{doc_id}'")
    return documents[doc_id]
