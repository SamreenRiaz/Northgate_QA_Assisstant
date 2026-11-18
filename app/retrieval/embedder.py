"""Turn text into vectors. This is the only module that knows which embedding model we use."""
from pathlib import Path
from typing import Protocol

from fastembed import TextEmbedding

from app.config import EMBEDDING_MODEL, MODELS_DIR

# bge models search better when the QUESTION (not the passage) starts with this instruction.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    """What the rest of the app needs from any embedder (the real one or a test fake)."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class BgeEmbedder:
    """bge-small-en-v1.5 run locally with fastembed. Vectors have 384 numbers and length 1."""

    def __init__(self, model_name: str = EMBEDDING_MODEL, cache_dir: Path = MODELS_DIR) -> None:
        # Downloads the model on first use (~67 MB), then loads it from cache_dir.
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed passages (chunks), as stored in the index."""
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        """Embed a user question, with the bge search instruction in front."""
        return self.embed_documents([QUERY_PREFIX + text])[0]
