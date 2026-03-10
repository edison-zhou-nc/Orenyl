from lore.embedding_provider import DeterministicHashEmbeddingProvider


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
