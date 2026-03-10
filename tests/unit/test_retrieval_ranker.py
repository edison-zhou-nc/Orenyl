from lore.retrieval_ranker import rank_items


def test_rrf_ranking_prefers_consistent_top_items():
    ranked = rank_items(
        item_ids=["fact:best", "fact:ok", "fact:weak"],
        keyword_order=["fact:best", "fact:ok", "fact:weak"],
        vector_order=["fact:ok", "fact:best", "fact:weak"],
        recency_order=["fact:best", "fact:weak", "fact:ok"],
        importance={"fact:best": 0.95, "fact:ok": 0.5, "fact:weak": 0.1},
    )
    assert ranked[0]["id"] == "fact:best"


def test_ranking_fallback_without_vector_order():
    ranked = rank_items(
        item_ids=["a", "b"],
        keyword_order=["b", "a"],
        vector_order=None,
        recency_order=["a", "b"],
        importance={"a": 0.4, "b": 0.7},
    )
    assert {row["id"] for row in ranked} == {"a", "b"}


def test_phase1_weights_make_vector_signal_dominant():
    ranked = rank_items(
        item_ids=["a", "b"],
        keyword_order=["a", "b"],
        vector_order=["b", "a"],
        recency_order=None,
        importance={"a": 0.5, "b": 0.5},
    )
    assert ranked[0]["id"] == "b"
