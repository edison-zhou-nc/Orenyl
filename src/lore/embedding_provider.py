"""Embedding provider abstractions and implementations."""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class EmbeddingProvider(Protocol):
    provider_id: str
    dim: int

    def embed_text(self, text: str) -> list[float]:
        ...


@dataclass
class DeterministicHashEmbeddingProvider:
    """Deterministic offline embedding provider for tests/dev fallback."""

    dim: int = 128
    provider_id: str = "hash-local"

    def embed_text(self, text: str) -> list[float]:
        seed = (text or "").strip().lower().encode("utf-8")
        if not seed:
            return [0.0] * self.dim

        values: list[float] = []
        counter = 0
        while len(values) < self.dim:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for idx in range(0, len(digest), 4):
                chunk = digest[idx: idx + 4]
                if len(chunk) < 4:
                    continue
                as_int = int.from_bytes(chunk, "big")
                values.append((as_int / 4294967295.0) * 2.0 - 1.0)
                if len(values) == self.dim:
                    break
            counter += 1

        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 0:
            return [0.0] * self.dim
        return [v / norm for v in values]


@dataclass
class OpenAIEmbeddingProvider:
    """Minimal OpenAI embedding adapter."""

    api_key: str
    model: str = "text-embedding-3-small"
    dim: int = 1536
    provider_id: str = "openai"
    timeout_seconds: float = 30.0

    def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("missing_openai_api_key")
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text or ""},
            )
            response.raise_for_status()
            payload = response.json()
            vector = payload["data"][0]["embedding"]
            return [float(v) for v in vector]


def build_embedding_provider_from_env() -> EmbeddingProvider:
    provider_name = os.environ.get("LORE_EMBEDDING_PROVIDER", "hash-local").strip().lower()
    if provider_name == "openai":
        api_key = os.environ.get("LORE_OPENAI_API_KEY", "")
        model = os.environ.get("LORE_EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddingProvider(api_key=api_key, model=model)

    dim = int(os.environ.get("LORE_EMBEDDING_DIM", "128"))
    return DeterministicHashEmbeddingProvider(dim=dim)
