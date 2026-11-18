"""Keyword search over chunks with BM25: finds exact words, names, numbers and codes."""
import re

from rank_bm25 import BM25Okapi

from app.ingestion.models import Chunk
from app.retrieval.models import SearchResult

# Lowercase words and numbers; keeps dotted numbers like "2026.22" and "4.2" together.
TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)*")


def tokenize(text: str) -> list[str]:
    """'Tier 1: $275, see 4.2 (VoyageHub)' -> ['tier', '1', '275', 'see', '4.2', 'voyagehub']"""
    return TOKEN.findall(text.lower())


class KeywordIndex:
    """BM25 over a list of chunks, kept in memory (rebuilt in well under a second)."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        # Section path is included, so words like "Travel Policy" or "Hotels" count too.
        corpus = [tokenize(f"{chunk.section} {chunk.text}") for chunk in self._chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, question: str, k: int = 5) -> list[SearchResult]:
        """Return up to k chunks sharing words with the question, best first (no-match chunks dropped)."""
        tokens = tokenize(question)
        if self._bm25 is None or not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(scores, self._chunks), key=lambda pair: pair[0], reverse=True)
        return [SearchResult(chunk=chunk, score=float(score)) for score, chunk in ranked[:k] if score > 0]
