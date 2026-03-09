from lore.semantic_dedup import is_semantic_duplicate


def test_is_semantic_duplicate_for_rephrased_same_fact():
    assert is_semantic_duplicate("i started metformin", "started metformin today") is True


def test_is_not_semantic_duplicate_for_different_fact():
    assert is_semantic_duplicate("started metformin", "role assigned admin") is False


def test_semantic_similarity_uses_union_denominator():
    assert is_semantic_duplicate("metformin", "metformin 500mg") is False
