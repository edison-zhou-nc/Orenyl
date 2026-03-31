import httpx
import pytest

from lore.embedding_provider import DeterministicHashEmbeddingProvider, OpenAIEmbeddingProvider


def test_deterministic_provider_returns_stable_vector():
    provider = DeterministicHashEmbeddingProvider(dim=8)
    first = provider.embed_text("started metformin")
    second = provider.embed_text("started metformin")
    assert len(first) == 8
    assert first == second


def test_deterministic_provider_normalizes_vector():
    provider = DeterministicHashEmbeddingProvider(dim=8)
    vector = provider.embed_text("role assigned admin")
    norm = sum(v * v for v in vector) ** 0.5
    assert 0.99 <= norm <= 1.01


def test_openai_provider_does_not_retry_on_unretryable_4xx(monkeypatch):
    class _Client:
        def __init__(self):
            self.calls = 0

        def post(self, *_args, **_kwargs):
            self.calls += 1
            request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    provider = OpenAIEmbeddingProvider(api_key="bad-key")
    provider._client = _Client()
    sleeps: list[float] = []
    monkeypatch.setattr("lore.embedding_provider.time.sleep", lambda value: sleeps.append(value))

    with pytest.raises(RuntimeError, match="embedding_provider_unavailable"):
        provider.embed_text("hello")

    assert provider._client.calls == 1
    assert sleeps == []


def test_openai_provider_retries_on_429(monkeypatch):
    class _Client:
        def __init__(self):
            self.calls = 0

        def post(self, *_args, **_kwargs):
            self.calls += 1
            request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
            if self.calls == 1:
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)
            return httpx.Response(
                200,
                request=request,
                json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
            )

    provider = OpenAIEmbeddingProvider(api_key="ok-key")
    provider._client = _Client()
    sleeps: list[float] = []
    monkeypatch.setattr("lore.embedding_provider.time.sleep", lambda value: sleeps.append(value))

    vector = provider.embed_text("hello")
    assert vector == [0.1, 0.2, 0.3]
    assert provider._client.calls == 2
    assert sleeps == [0.5]


def test_openai_provider_client_field_not_exposed_in_init():
    assert OpenAIEmbeddingProvider.__dataclass_fields__["_client"].init is False


def test_openai_provider_close_closes_http_client():
    class _Client:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    provider = OpenAIEmbeddingProvider(api_key="ok-key")
    client = _Client()
    provider._client = client

    provider.close()

    assert client.closed is True
    assert provider._client is None


def test_openai_provider_del_closes_http_client():
    class _Client:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    provider = OpenAIEmbeddingProvider(api_key="ok-key")
    client = _Client()
    provider._client = client

    provider.__del__()

    assert client.closed is True
    assert provider._client is None
