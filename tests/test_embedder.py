"""Tests for the real embedding model. Marked slow: the first run downloads the model."""
import math

import pytest

from app.retrieval.embedder import BgeEmbedder

pytestmark = pytest.mark.slow  # every test in this file; skip with: pytest -m "not slow"


@pytest.fixture(scope="module")
def embedder():
    """Load the model once for this file."""
    return BgeEmbedder()


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_vector_size_and_length(embedder):
    [vector] = embedder.embed_documents(["Hotel room rates are capped per night."])
    assert len(vector) == 384
    assert math.isclose(math.sqrt(dot(vector, vector)), 1.0, abs_tol=1e-3)  # normalized


def test_one_vector_per_text(embedder):
    vectors = embedder.embed_documents(["first text", "second text", "third text"])
    assert len(vectors) == 3


def test_query_prefix_changes_vector(embedder):
    assert embedder.embed_query("hotel rates") != embedder.embed_documents(["hotel rates"])[0]


def test_question_closest_to_matching_passage(embedder):
    hotel, vpn = embedder.embed_documents(
        [
            "Hotel room rates are capped per night: Tier 1 $275, Tier 2 $200.",
            "You may hold at most 2 concurrent VPN sessions.",
        ]
    )
    question = embedder.embed_query("How much can I spend on a hotel in Boston?")
    assert dot(question, hotel) > dot(question, vpn)  # vectors are normalized, so dot = cosine
