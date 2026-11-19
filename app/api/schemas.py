"""Shapes of the JSON the API accepts and returns. Pydantic validates them and documents them at /docs."""
from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=500)


class CitationOut(BaseModel):
    number: int  # the [n] used in the answer text
    doc_id: str
    title: str
    section: str
    text: str  # the cited passage, to highlight in the source viewer
    effective_date: str
    labels: list[str]  # e.g. "NOT YET IN EFFECT until 2027-01-01", "meeting notes"


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationOut]


class DocumentOut(BaseModel):
    doc_id: str
    title: str
    text: str
    metadata: dict[str, str]
