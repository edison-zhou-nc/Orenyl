from lore.semantic_dedup import cosine_similarity, is_semantic_duplicate_by_embedding


def test_cosine_similarity_detects_near_duplicate_vectors():
    score = cosine_similarity([1.0, 0.0], [0.98, 0.02])
    assert score > 0.97


def test_embedding_duplicate_threshold_behavior():
    assert is_semantic_duplicate_by_embedding([1.0, 0.0], [0.99, 0.01], threshold=0.95) is True
    assert is_semantic_duplicate_by_embedding([1.0, 0.0], [0.4, 0.6], threshold=0.95) is False


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
