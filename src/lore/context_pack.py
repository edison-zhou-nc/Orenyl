"""Context pack builder: assembles bounded, traced context for agents."""

from __future__ import annotations

import json

from .db import Database
from .models import ContextPack, RecallTrace
from .retrieval_ranker import rank_items


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
        agent_id: str = "",
        session_id: str = "",
    ) -> ContextPack:
        """Build a context pack from current valid facts with trace."""
        if not should_retrieve(query):
            return ContextPack(
                domain=domain,
                event_count=self.db.get_event_count(domain),
                latest_event=self.db.get_latest_event_ts(domain),
                drill_down_available=False,
                facts=[],
                summary="" if include_summary else "",
                items=[],
                trace={"query": query, "included": [], "max_sensitivity": max_sensitivity},
            )

        facts = self.db.get_current_facts_by_domain(
            domain,
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

        # Vector order is optional in v2.1; None means deterministic fallback path.
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
        parent_edges_by_fact = self.db.get_parents_for_children(ranked_fact_ids)
        parent_event_ids = sorted(
            {
                edge["parent_id"]
                for edges in parent_edges_by_fact.values()
                for edge in edges
                if edge.get("parent_type") == "event"
            }
        )
        parent_events_by_id = self.db.get_events_by_ids(parent_event_ids)

        items = []
        for ranked in ranking[:limit]:
            fact = id_to_fact[ranked["id"]]
            # Build provenance from lineage edges
            parents = parent_edges_by_fact.get(fact["id"], [])
            derived_from = [p["parent_id"] for p in parents]
            parent_events = [
                parent_events_by_id.get(pid) for pid in derived_from
            ]
            parent_levels = [
                (e or {}).get("sensitivity", "medium").lower() for e in parent_events if e
            ]
            fact_sensitivity = "medium"
            if parent_levels:
                fact_sensitivity = max(parent_levels, key=lambda level: sensitivity_rank.get(level, 2))
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

        event_count = self.db.get_event_count(domain)
        latest_event = self.db.get_latest_event_ts(domain)
        summary = f"{len(items)} fact(s) from domain '{domain}'" if include_summary else ""

        pack = ContextPack(
            domain=domain,
            event_count=event_count,
            latest_event=latest_event,
            drill_down_available=True,
            facts=items,
            summary=summary,
            items=items,
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
