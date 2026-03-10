"""Hybrid ranking utilities for context-pack retrieval."""

from __future__ import annotations


def _rrf_score(order: list[str] | None, k: int = 60) -> dict[str, float]:
    if not order:
        return {}
    return {item_id: 1.0 / (k + rank) for rank, item_id in enumerate(order, start=1)}


def rank_items(
    item_ids: list[str],
    keyword_order: list[str] | None,
    vector_order: list[str] | None,
    recency_order: list[str] | None,
    importance: dict[str, float] | None = None,
) -> list[dict]:
    # When vector_order is absent, vector contribution remains 0.0 and weights are not renormalized.
    # This keeps fallback scoring conservative and stable until vector signals are explicitly provided.
    importance = importance or {}
    keyword_scores = _rrf_score(keyword_order)
    vector_scores = _rrf_score(vector_order)
    recency_scores = _rrf_score(recency_order)

    result = []
    for item_id in item_ids:
        score = 0.0
        score += keyword_scores.get(item_id, 0.0) * 0.30
        score += vector_scores.get(item_id, 0.0) * 0.40
        score += recency_scores.get(item_id, 0.0) * 0.15
        score += float(importance.get(item_id, 0.5)) * 0.15
        result.append({"id": item_id, "score": score})

    result.sort(key=lambda row: (-row["score"], row["id"]))
    return result
