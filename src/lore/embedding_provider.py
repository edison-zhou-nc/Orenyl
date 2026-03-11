"""Embedding provider abstractions and implementations."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


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
    max_retries: int = 2
    backoff_seconds: float = 0.5
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("missing_openai_api_key")
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_seconds)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.post(
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
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if not _is_retryable_status(exc.response.status_code):
                    break
                if attempt >= self.max_retries:
                    break
                time.sleep(self.backoff_seconds * (attempt + 1))
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.backoff_seconds * (attempt + 1))
        raise RuntimeError("embedding_provider_unavailable") from last_error


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def build_embedding_provider_from_env() -> EmbeddingProvider:
    provider_name = os.environ.get("LORE_EMBEDDING_PROVIDER", "hash-local").strip().lower()
    if provider_name == "openai":
        api_key = os.environ.get("LORE_OPENAI_API_KEY", "")
        model = os.environ.get("LORE_EMBEDDING_MODEL", "text-embedding-3-small")
        if os.environ.get("LORE_EMBEDDING_DIM", "").strip():
            logger.warning(
                "LORE_EMBEDDING_DIM is ignored when LORE_EMBEDDING_PROVIDER=openai; provider dimensions are model-defined"
            )
        return OpenAIEmbeddingProvider(api_key=api_key, model=model)

    dim = int(os.environ.get("LORE_EMBEDDING_DIM", "128"))
    return DeterministicHashEmbeddingProvider(dim=dim)
