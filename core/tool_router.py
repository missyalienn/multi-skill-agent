"""
Semantic Tool Selection.

Instead of handing the model a flat list of every tool on every call, embed
each tool's description once, embed the incoming query, and route to the
most relevant tool(s) by cosine similarity. This is the most common, most
recommended pattern for tool selection -- faster and more scalable than
letting the model freely reason over every tool every time.

The embedder is swappable. TfidfEmbedder below is a local, dependency-light
stand-in that needs no API key and works fully offline -- good for a
runnable demo. In production, swap in a real embedding model (Voyage AI is
Anthropic's recommended embeddings partner, or OpenAI's embedding models)
by implementing the same `embed(texts: list[str]) -> np.ndarray` interface.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.tools import ToolSpec, ToolCategory


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


class TfidfEmbedder:
    """Local, no-API-key embedder. Good for demos and tests; swap for a
    real embedding model (Voyage, OpenAI, Cohere) in production -- the
    routing logic below doesn't change either way."""

    def __init__(self):
        self._vectorizer = TfidfVectorizer()
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._vectorizer.fit(corpus)
        self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Embedder must be fit on the tool corpus before use.")
        return self._vectorizer.transform(texts).toarray()


class ToolRouter:
    """Registers tools, embeds their descriptions, and routes queries to
    the top-k most semantically relevant tools."""

    def __init__(self, tools: list[ToolSpec], embedder: Embedder | None = None):
        self.tools = tools
        self.embedder = embedder or TfidfEmbedder()

        descriptions = [t.description for t in tools]
        if isinstance(self.embedder, TfidfEmbedder):
            self.embedder.fit(descriptions)
        self._tool_embeddings = self.embedder.embed(descriptions)

    def select(self, query: str, top_k: int = 1) -> list[tuple[ToolSpec, float]]:
        query_embedding = self.embedder.embed([query])
        scores = cosine_similarity(query_embedding, self._tool_embeddings)[0]

        ranked = sorted(zip(self.tools, scores), key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]
