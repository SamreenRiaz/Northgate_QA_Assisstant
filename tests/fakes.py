"""Fast, offline stand-ins for the real embedder, LLM and retriever. No model, no network, no tokens."""
import math
import re
import zlib


class FakeEmbedder:
    """Each word adds 1 to one of 64 positions (chosen by a fixed hash), then the vector is
    scaled to length 1. Texts that share words get similar vectors.
    """

    DIMENSIONS = 64

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.DIMENSIONS
        for word in re.findall(r"[a-z0-9$]+", text.lower()):
            vector[zlib.crc32(word.encode()) % self.DIMENSIONS] += 1.0
        length = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / length for x in vector]


class FakeLLM:
    """Returns a fixed reply and remembers every prompt it got."""

    def __init__(self, reply: str = "The handbook does not cover this.") -> None:
        self.reply = reply
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        return self.reply


class FakeRetriever:
    """Returns fixed search results and remembers the last question."""

    def __init__(self, results: list) -> None:
        self.results = results
        self.asked: tuple[str, int] | None = None

    def search(self, question: str, k: int) -> list:
        self.asked = (question, k)
        return self.results[:k]
