"""Context pack builder: assembles bounded, traced context for agents."""

from __future__ import annotations

import json
import logging

from .config import compliance_strict_mode_enabled, min_fact_confidence_threshold
from .db import Database
from .embedding_provider import build_embedding_provider_from_env
from .embeddings import cosine_similarity
from .models import ContextPack, RecallTrace
from .retrieval_ranker import rank_items
from .vector_backend import build_vector_backend_from_env

_embedding_provider = None
_vector_backend = None
logger = logging.getLogger(__name__)


def _get_embedding_provider():
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = build_embedding_provider_from_env()
    return _embedding_provider


def _get_vector_backend(db: Database):
    global _vector_backend
    if _vector_backend is None:
        _vector_backend = build_vector_backend_from_env(db)
    return _vector_backend


def _reset_runtime_state_for_tests() -> None:
    global _embedding_provider, _vector_backend
    _embedding_provider = None
    _vector_backend = None


def should_retrieve(query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    small_talk = {"hi", "hello", "thanks", "thank you", "good morning", "hello there"}
    if q in small_talk:
        return False
    if "remember" in q or "memory" in q:
        return True
    return q not in {"hey"}


def backfill_missing_fact_embeddings(db: Database, fact_ids: list[str], tenant_id: str = "") -> int:
    if not fact_ids:
        return 0
    provider = _get_embedding_provider()
    facts = db.get_facts_by_ids(fact_ids, tenant_id=tenant_id)
    existing = db.get_fact_embeddings([fact["id"] for fact in facts], tenant_id=tenant_id)
    created = 0
    for fact in facts:
        if fact["id"] in existing:
            continue
        fact_text = f"{fact.get('key', '')}:{json.dumps(fact.get('value', ''), sort_keys=True)}"
        try:
            fact_vector = provider.embed_text(fact_text)
            db.upsert_fact_embedding(
                fact["id"],
                fact_vector,
                provider.provider_id,
                tenant_id=fact.get("tenant_id", tenant_id or "default"),
            )
            created += 1
        except Exception as exc:
            logger.warning("fact_embedding_backfill_failed fact_id=%s error=%s", fact["id"], exc)
    return created


class ContextPackBuilder:
    def __init__(self, db: Database):
        self.db = db

    def build(
        self,
        domain: str = "general",
        include_summary: bool = True,
        max_sensitivity: str = "high",
        limit: int = 50,
        query: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        session_id: str = "",
    ) -> ContextPack:
        """Build a context pack from current valid facts with trace."""
        if not should_retrieve(query):
            return ContextPack(
                domain=domain,
                event_count=self.db.get_event_count(domain, tenant_id=tenant_id),
                latest_event=self.db.get_latest_event_ts(domain, tenant_id=tenant_id),
                drill_down_available=False,
                facts=[],
                summary="" if include_summary else "",
                items=[],
                trace={"query": query, "included": [], "max_sensitivity": max_sensitivity},
            )

        facts = self.db.get_current_facts_by_domain(
            domain,
            tenant_id=tenant_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        trace = RecallTrace(query=query)
        sensitivity_rank = {"low": 0, "medium": 1, "high": 2, "restricted": 3}
        max_rank = sensitivity_rank.get((max_sensitivity or "high").lower(), 2)

        sorted_by_recency = sorted(
            facts,
            key=lambda f: (f.get("created_at") or f.get("valid_from") or ""),
            reverse=True,
        )
        recency_order = [fact["id"] for fact in sorted_by_recency]
        id_to_fact = {fact["id"]: fact for fact in facts}

        query_tokens = [tok for tok in (query or "").lower().split() if tok]
        keyword_scored: list[tuple[int, str]] = []
        for fact in facts:
            key_text = str(fact.get("key", "")).lower()
            value_text = json.dumps(fact.get("value", ""), sort_keys=True).lower()
            hit_count = sum(1 for tok in query_tokens if tok in key_text or tok in value_text)
            keyword_scored.append((hit_count, fact["id"]))
        keyword_scored.sort(key=lambda row: (-row[0], row[1]))
        keyword_order = [item_id for _, item_id in keyword_scored]

        vector_order = None
        try:
            provider = _get_embedding_provider()
            query_vector = provider.embed_text(query or domain or "general")
            stored_fact_embeddings = self.db.get_fact_embeddings(
                [fact["id"] for fact in facts],
                tenant_id=tenant_id,
            )
            has_model_or_dim_mismatch = False
            for fact in facts:
                existing = stored_fact_embeddings.get(fact["id"])
                if existing is None:
                    continue
                if str(existing.get("model_id", "")) != str(provider.provider_id):
                    logger.warning(
                        (
                            "context_pack_embedding_model_mismatch "
                            "fact_id=%s stored_model=%s provider=%s"
                        ),
                        fact["id"],
                        existing.get("model_id"),
                        provider.provider_id,
                    )
                    has_model_or_dim_mismatch = True
                    continue
                if len(existing["vector"]) != len(query_vector):
                    logger.warning(
                        (
                            "context_pack_embedding_dim_mismatch "
                            "fact_id=%s stored_dim=%s query_dim=%s"
                        ),
                        fact["id"],
                        len(existing["vector"]),
                        len(query_vector),
                    )
                    has_model_or_dim_mismatch = True

            backend = _get_vector_backend(self.db)
            raw_order = backend.query(
                namespace=tenant_id or "default",
                query=query_vector,
                top_k=max(limit * 3, len(facts)),
            )
            allowed_ids = {fact["id"] for fact in facts}
            vector_order = [item_id for item_id in raw_order if item_id in allowed_ids]
            if not vector_order or has_model_or_dim_mismatch:
                vector_scored: list[tuple[float, str]] = []
                for fact in facts:
                    existing = stored_fact_embeddings.get(fact["id"])
                    if existing is not None:
                        if str(existing.get("model_id", "")) != str(provider.provider_id):
                            logger.warning(
                                (
                                    "context_pack_embedding_model_mismatch "
                                    "fact_id=%s stored_model=%s provider=%s"
                                ),
                                fact["id"],
                                existing.get("model_id"),
                                provider.provider_id,
                            )
                            existing = None
                        elif len(existing["vector"]) != len(query_vector):
                            logger.warning(
                                (
                                    "context_pack_embedding_dim_mismatch "
                                    "fact_id=%s stored_dim=%s query_dim=%s"
                                ),
                                fact["id"],
                                len(existing["vector"]),
                                len(query_vector),
                            )
                            existing = None
                    if existing is not None:
                        fact_vector = existing["vector"]
                    else:
                        fact_text = (
                            f"{fact.get('key', '')}:"
                            f"{json.dumps(fact.get('value', ''), sort_keys=True)}"
                        )
                        fact_vector = provider.embed_text(fact_text)
                    similarity = cosine_similarity(query_vector, fact_vector)
                    vector_scored.append((similarity, fact["id"]))
                vector_scored.sort(key=lambda row: (-row[0], row[1]))
                vector_order = [item_id for _, item_id in vector_scored]
        except Exception as exc:
            logger.warning("embedding_pipeline_fallback domain=%s error=%s", domain, exc)
            vector_order = None
        importance_map = {fact["id"]: float(fact.get("importance", 0.5)) for fact in facts}
        ranking = rank_items(
            item_ids=[fact["id"] for fact in facts],
            keyword_order=keyword_order,
            vector_order=vector_order,
            recency_order=recency_order,
            importance=importance_map,
        )

        ranked_fact_ids = [ranked["id"] for ranked in ranking[:limit]]
        parent_edges_by_fact = self.db.get_parents_for_children(
            ranked_fact_ids,
            tenant_id=tenant_id,
        )
        parent_event_ids = sorted(
            {
                edge["parent_id"]
                for edges in parent_edges_by_fact.values()
                for edge in edges
                if edge.get("parent_type") == "event"
            }
        )
        parent_events_by_id = self.db.get_events_by_ids(parent_event_ids, tenant_id=tenant_id)
        withdrawn_subject_ids: set[str] = set()
        if compliance_strict_mode_enabled():
            all_subject_ids = sorted(
                {
                    str((event or {}).get("metadata", {}).get("subject_id", "")).strip()
                    for event in parent_events_by_id.values()
                    if event
                }
            )
            withdrawn_subject_ids = self.db.withdrawn_subject_ids(
                subject_ids=[subject_id for subject_id in all_subject_ids if subject_id],
                purpose="retrieval",
                tenant_id=tenant_id,
            )

        items = []
        min_confidence = min_fact_confidence_threshold()
        for ranked in ranking[:limit]:
            fact = id_to_fact[ranked["id"]]
            if float(fact.get("confidence", 1.0)) < min_confidence:
                continue
            # Build provenance from lineage edges
            parents = parent_edges_by_fact.get(fact["id"], [])
            derived_from = [p["parent_id"] for p in parents]
            parent_events = [
                parent_events_by_id.get(pid) for pid in derived_from
            ]
            if withdrawn_subject_ids:
                subject_ids = {
                    str((event or {}).get("metadata", {}).get("subject_id", "")).strip()
                    for event in parent_events
                    if event
                }
                subject_ids = {subject_id for subject_id in subject_ids if subject_id}
                withdrawn = bool(subject_ids & withdrawn_subject_ids)
                if withdrawn:
                    continue
            parent_levels = [
                (e or {}).get("sensitivity", "medium").lower() for e in parent_events if e
            ]
            fact_sensitivity = "medium"
            if parent_levels:
                fact_sensitivity = max(
                    parent_levels,
                    key=lambda level: sensitivity_rank.get(level, 2),
                )
            if sensitivity_rank.get(fact_sensitivity, 2) > max_rank:
                continue

            item = {
                "id": fact["id"],
                "type": "fact",
                "key": fact["key"],
                "value": fact["value"],
                "sensitivity": fact_sensitivity,
                "validity": {
                    "from": fact["valid_from"],
                    "to": fact["valid_to"],
                },
                "provenance": {
                    "derived_from": derived_from,
                    "rule": fact["rule_id"],
                    "version": fact["version"],
                },
                "score": ranked["score"],
            }
            items.append(item)

            # Build trace entry
            why = [f"current_valid_fact:{fact['key']}"]
            if query:
                # Simple keyword matching for trace explanation
                query_lower = query.lower()
                key_lower = fact["key"].lower()
                if any(word in key_lower for word in query_lower.split()):
                    why.append(f"key_match:{fact['key']}")
                why.append(f"rule_output:{fact['rule_id']}")

            trace.add_item(
                item_id=fact["id"],
                why=why,
                lineage=derived_from,
            )

        event_count = self.db.get_event_count(domain, tenant_id=tenant_id)
        latest_event = self.db.get_latest_event_ts(domain, tenant_id=tenant_id)
        summary = f"{len(items)} fact(s) from domain '{domain}'" if include_summary else ""

        pack = ContextPack(
            domain=domain,
            event_count=event_count,
            latest_event=latest_event,
            drill_down_available=True,
            facts=list(items),
            summary=summary,
            items=list(items),
            trace={
                "query": query,
                "included": trace.included,
                "max_sensitivity": max_sensitivity,
                "agent_id": agent_id or None,
                "session_id": session_id or None,
            },
        )

        # Log the retrieval
        self.db.log_retrieval(
            query=query,
            context_pack=pack.to_json(),
            trace=json.dumps(trace.included),
        )

        return pack
