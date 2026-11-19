"""Shared fixtures. pytest loads this file automatically for every test."""
import pytest

from tests.fakes import FakeEmbedder, FakeLLM


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def fake_llm():
    return FakeLLM()
