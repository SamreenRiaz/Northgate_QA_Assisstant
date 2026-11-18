"""Data shapes shared by the retrieval modules."""
from dataclasses import dataclass

from app.ingestion.models import Chunk


@dataclass
class SearchResult:
    """One matching chunk and how well it matched one question (higher = better)."""

    chunk: Chunk
    score: float
