"""Answer a question: retrieve passages, ask the model, and return the answer with its sources."""
import re
from dataclasses import dataclass
from typing import Protocol

from app.config import TOP_K, today
from app.generation.llm import LLM
from app.generation.prompts import build_messages
from app.ingestion.models import Chunk
from app.retrieval.models import SearchResult

# "[2]", "[2][3]" and "[2, 3]" all cite passages by number.
CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# Some models (gpt-oss) cite in their own style, "【2】" or "【2†L4-L6】"; we rewrite these to "[2]".
MODEL_CITATION = re.compile(r"【(\d+)(?:†[^】]*)?】")


class Retriever(Protocol):
    def search(self, question: str, k: int) -> list[SearchResult]: ...


@dataclass
class Citation:
    number: int  # the [n] used in the answer text
    chunk: Chunk  # the passage it points to


@dataclass
class Answer:
    text: str
    citations: list[Citation]  # only the passages the answer actually cites


class Answerer:
    def __init__(self, retriever: Retriever, llm: LLM, k: int = TOP_K) -> None:
        self._retriever = retriever
        self._llm = llm
        self._k = k

    def answer(self, question: str) -> Answer:
        results = self._retriever.search(question, k=self._k)
        reply = self._llm.complete(build_messages(question, results, today()))
        text = MODEL_CITATION.sub(r"[\1]", reply)
        return Answer(text=text, citations=cited_passages(text, results))


def cited_passages(text: str, results: list[SearchResult]) -> list[Citation]:
    """Map the [n] markers in the answer back to the passages, in number order.

    Numbers outside 1..len(results) are ignored: the model cannot cite a passage it never saw.
    """
    numbers = {int(number) for group in CITATION.findall(text) for number in group.split(",")}
    return [Citation(n, results[n - 1].chunk) for n in sorted(numbers) if 1 <= n <= len(results)]
