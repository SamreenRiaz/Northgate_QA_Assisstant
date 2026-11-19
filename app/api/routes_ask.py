"""POST /api/ask: answer a question with citations."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_answerer
from app.api.schemas import AskRequest, AskResponse, CitationOut
from app.config import today
from app.generation.answerer import Answerer, Citation
from app.generation.llm import LLMError
from app.generation.prompts import source_labels

router = APIRouter(prefix="/api")


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, answerer: Answerer = Depends(get_answerer)) -> AskResponse:
    try:
        answer = answerer.answer(request.question)
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AskResponse(answer=answer.text, citations=[to_citation_out(c) for c in answer.citations])


def to_citation_out(citation: Citation) -> CitationOut:
    chunk = citation.chunk
    return CitationOut(
        number=citation.number,
        doc_id=chunk.doc_id,
        title=chunk.metadata["title"],
        section=chunk.section,
        text=chunk.text,
        effective_date=chunk.metadata["effective_date"],
        labels=source_labels(chunk.metadata, today()),
    )
