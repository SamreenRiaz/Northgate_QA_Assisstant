"""Shared test helpers. pytest loads this file automatically for every test."""
import math
import re
import zlib

import pytest


class FakeEmbedder:
    """Fast, offline stand-in for BgeEmbedder.

    Each word adds 1 to one of 64 positions (chosen by a fixed hash), then the vector is
    scaled to length 1. Texts that share words get similar vectors. No model, no download.
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


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()
