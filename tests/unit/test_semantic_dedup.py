from orenyl.db import Database
from orenyl.models import Event
from orenyl.semantic_dedup import (
    check_semantic_duplicate,
    cosine_similarity,
    is_semantic_duplicate_by_embedding,
)


def test_cosine_similarity_detects_near_duplicate_vectors():
    score = cosine_similarity([1.0, 0.0], [0.98, 0.02])
    assert score > 0.97


def test_embedding_duplicate_threshold_behavior():
    assert is_semantic_duplicate_by_embedding([1.0, 0.0], [0.99, 0.01], threshold=0.95) is True
    assert is_semantic_duplicate_by_embedding([1.0, 0.0], [0.4, 0.6], threshold=0.95) is False


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_check_semantic_duplicate_uses_stored_event_embeddings():
    class _Provider:
        provider_id = "test-provider"

        def __init__(self):
            self.calls = 0

        def embed_text(self, text: str) -> list[float]:
            self.calls += 1
            return [1.0, 0.0]

    db = Database(":memory:")
    event = Event(
        id="event:test:existing",
        type="note",
        payload={"text": "started metformin"},
        domains=["health"],
    )
    db.insert_event(event)
    db.upsert_event_embedding(event.id, [1.0, 0.0], "test-provider")

    provider = _Provider()
    is_dup, existing_id = check_semantic_duplicate(
        db=db,
        provider=provider,
        content="began taking medication",
        domains=["health"],
        threshold=0.95,
    )
    assert is_dup is True
    assert existing_id == event.id
    assert provider.calls == 1
