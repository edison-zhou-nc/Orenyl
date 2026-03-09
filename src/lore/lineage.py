"""Lineage: delete propagation + rederivation.

This is the entire thesis in one module.
"""

from __future__ import annotations
import sqlite3

from typing import Any

from .db import Database
from .models import DeleteProof, Edge, Fact, Tombstone, now_iso
from .rules import ALL_RULES, RULE_REGISTRY, get_rules_for_event_type


class LineageEngine:
    def __init__(self, db: Database):
        self.db = db

    def _resolve_rule_specs(self, event: dict | None) -> list[dict]:
        if not event:
            return []

        specs: dict[str, dict] = {}
        event_type = event.get("type", "")
        domains = event.get("domains") or []
        clean_domains = [d for d in domains if d]

        # Preserve v1 behavior for events that were not domain-tagged.
        for rule in get_rules_for_event_type(event_type):
            specs[rule.output_key] = {
                "rule": rule,
                "source": "event_type",
                "domains": [],
            }

        # Domain-selected rules are additive and can handle new event types (e.g. note).
        if clean_domains:
            for rule in RULE_REGISTRY.get_rules_for_domains(clean_domains):
                existing = specs.get(rule.output_key)
                if existing and existing["source"] == "event_type":
                    specs[rule.output_key] = {
                        "rule": rule,
                        "source": "hybrid",
                        "domains": clean_domains,
                    }
                else:
                    specs[rule.output_key] = {
                        "rule": rule,
                        "source": "domain",
                        "domains": clean_domains,
                    }

        return list(specs.values())

    def _collect_events_for_rule(self, spec: dict) -> list[dict]:
        rule = spec["rule"]
        source = spec["source"]
        domains = spec["domains"]

        if source == "domain":
            return self.db.get_active_events_by_domains(domains)
        if source == "hybrid":
            by_id: dict[str, dict] = {}
            for event in self.db.get_active_events_by_domains(domains):
                by_id[event["id"]] = event
            for et in rule.relevant_event_types():
                for event in self.db.get_active_events(et):
                    by_id[event["id"]] = event
            return [by_id[k] for k in sorted(by_id.keys())]

        all_events: list[dict] = []
        for et in rule.relevant_event_types():
            all_events.extend(self.db.get_active_events(et))
        return all_events

    def _insert_fact_with_retry(self, rule, value: Any, max_retries: int = 3) -> Fact:
        last_error: sqlite3.IntegrityError | None = None
        for _ in range(max_retries):
            try:
                next_version = self.db.get_latest_version(rule.output_key) + 1
                fact = Fact(
                    id=f"fact:{rule.output_key}:v{next_version}",
                    key=rule.output_key,
                    value=value,
                    version=next_version,
                    rule_id=rule.rule_id,
                )
                self.db.insert_fact(fact)
                # Invalidate previous versions only after the replacement fact is persisted.
                all_versions = self.db.get_facts_by_key(rule.output_key)
                for old_fact in all_versions:
                    if old_fact.get("invalidated_at") is not None:
                        continue
                    if old_fact["id"] == fact.id:
                        continue
                    self.db.invalidate_fact(
                        old_fact["id"],
                        reason=f"superseded_by_v{next_version}",
                        invalidated_at=now_iso(),
                    )
                return fact
            except sqlite3.IntegrityError as exc:
                last_error = exc
                continue

        raise RuntimeError(
            f"fact_version_conflict:{rule.output_key}:retries_exhausted"
        ) from last_error

    def derive_facts_for_event(self, event: dict) -> list[str]:
        """After storing an event, derive/update all relevant facts."""
        created_fact_ids: list[str] = []
        with self.db.transaction():
            for spec in self._resolve_rule_specs(event):
                rule = spec["rule"]
                all_events = self._collect_events_for_rule(spec)

                # Run deterministic derivation
                value = rule.derive(all_events)

                fact = self._insert_fact_with_retry(rule, value)
                fact_id = fact.id

                # Create lineage edges from all contributing events
                for ev in all_events:
                    self.db.insert_edge(Edge(
                        parent_id=ev["id"],
                        parent_type="event",
                        child_id=fact_id,
                        child_type="fact",
                    ))

                created_fact_ids.append(fact_id)

        return created_fact_ids

    def delete_and_recompute(
        self,
        target_id: str,
        target_type: str,
        reason: str = "",
        mode: str = "soft",
        run_vacuum: bool = False,
    ) -> DeleteProof:
        """The killer feature.

        1. Tombstone the target
        2. Find all downstream facts
        3. Invalidate them
        4. Re-derive from remaining active events
        5. Return proof of everything that happened
        """
        ts = now_iso()
        proof = DeleteProof(
            target_id=target_id,
            target_type=target_type,
            reason=reason,
        )
        skip_count = 0
        stale_marked_count = 0
        domain_scoped = False
        downstream_ids: list[str] = []
        tombstone_recorded = False

        event_data: dict | None = None
        # Step 1: Tombstone or hard-delete the target
        with self.db.transaction():
            if target_type == "event":
                event_data = self.db.get_event(target_id)
                if event_data is None:
                    skip_count = 1
                    proof.checks = {
                        "error": "Event not found or already deleted",
                        "skip_count": skip_count,
                        "domain_scoped": False,
                        "stale_marked": stale_marked_count,
                        "deletion_verified": True,
                        "resurfaced_references": [],
                        "target_in_active_events": False,
                    }
                    proof.post_delete_check = dict(proof.checks)
                    return proof
                domain_scoped = bool(event_data.get("domains"))

                if mode == "hard":
                    # Record audit evidence before physical erasure.
                    downstream_ids = self.db.get_downstream_facts(target_id)
                    self.db.insert_tombstone(
                        Tombstone(
                            target_id=target_id,
                            target_type=target_type,
                            reason=reason,
                            deleted_at=ts,
                            cascade_invalidated=downstream_ids,
                        )
                    )
                    tombstone_recorded = True

                if mode == "hard":
                    self.db.hard_delete_facts_by_source(target_id)
                    self.db.delete_edges_for_item(target_id)
                    success = self.db.hard_delete_event(target_id)
                else:
                    success = self.db.soft_delete_event(target_id, ts)
                if not success:
                    proof.checks = {"error": "Event not found or already deleted"}
                    proof.post_delete_check = dict(proof.checks)
                    return proof
                proof.tombstoned.append(target_id)

            elif target_type == "fact":
                success = self.db.invalidate_fact(target_id, reason=reason, invalidated_at=ts)
                if not success:
                    proof.checks = {"error": "Fact not found or already invalidated"}
                    proof.post_delete_check = dict(proof.checks)
                    return proof
                proof.tombstoned.append(target_id)

            # Step 2: Find all downstream facts
            if not downstream_ids:
                downstream_ids = self.db.get_downstream_facts(target_id)

            # Step 3: Invalidate downstream facts
            stale_marked_count = self.db.mark_facts_stale(downstream_ids)
            for fact_id in downstream_ids:
                was_invalidated = self.db.invalidate_fact(
                    fact_id,
                    reason=f"cascade_from:{target_id}",
                    invalidated_at=ts,
                )
                if was_invalidated:
                    proof.invalidated_facts.append(fact_id)

            # Record tombstone with cascade info for non-hard-delete paths.
            if not tombstone_recorded:
                tombstone = Tombstone(
                    target_id=target_id,
                    target_type=target_type,
                    reason=reason,
                    deleted_at=ts,
                    cascade_invalidated=proof.invalidated_facts,
                )
                self.db.insert_tombstone(tombstone)

            # Step 4: Re-derive facts from remaining active events
            # Figure out which rules need re-running
            rules_to_rerun: dict[str, dict] = {}
            if target_type == "event":
                for spec in self._resolve_rule_specs(event_data):
                    rules_to_rerun[spec["rule"].output_key] = spec
            else:
                # If a fact was deleted, find what rule produced it
                fact_data = self.db.get_fact(target_id)
                if fact_data:
                    parent_events = [
                        self.db.get_event(parent["parent_id"])
                        for parent in self.db.get_parents(target_id)
                        if parent["parent_type"] == "event"
                    ]
                    for parent_event in parent_events:
                        for spec in self._resolve_rule_specs(parent_event):
                            rules_to_rerun[spec["rule"].output_key] = spec
                    if not rules_to_rerun:
                        for rule in ALL_RULES:
                            if rule.output_key == fact_data["key"]:
                                rules_to_rerun[rule.output_key] = {
                                    "rule": rule,
                                    "source": "event_type",
                                    "domains": [],
                                }
                                break

            for spec in rules_to_rerun.values():
                rule = spec["rule"]
                all_events = self._collect_events_for_rule(spec)

                # Re-derive
                value = rule.derive(all_events)
                fact = self._insert_fact_with_retry(rule, value)
                fact_id = fact.id

                # Create lineage edges from remaining events
                for ev in all_events:
                    self.db.insert_edge(Edge(
                        parent_id=ev["id"],
                        parent_type="event",
                        child_id=fact_id,
                        child_type="fact",
                    ))

                proof.rederived_facts.append({
                    "fact_id": fact_id,
                    "key": rule.output_key,
                    "value": value,
                    "version": fact.version,
                    "derived_from_events": [e["id"] for e in all_events],
                })

            # Step 5: Post-delete retrieval check
            # Verify deleted content cannot resurface.
            current_facts = self.db.get_current_facts()
            resurfaced = []
            for f in current_facts:
                parents = self.db.get_parents(f["id"])
                for p in parents:
                    if p["parent_id"] == target_id:
                        resurfaced.append(f["id"])

            target_event = self.db.get_event(target_id) if target_type == "event" else None
            if target_type == "fact" and not domain_scoped:
                domain_scoped = any(spec.get("source") in {"domain", "hybrid"} for spec in rules_to_rerun.values())
            proof.checks = {
                "target_in_active_events": bool(target_event and target_event.get("deleted_at") is None),
                "resurfaced_references": resurfaced,
                "deletion_verified": len(resurfaced) == 0,
                "skip_count": skip_count,
                "domain_scoped": domain_scoped,
                "stale_marked": stale_marked_count,
                "vacuum_ran": False,
            }
        if mode == "hard" and run_vacuum:
            self.db.run_vacuum()
            proof.checks["vacuum_ran"] = True
        proof.post_delete_check = dict(proof.checks)

        return proof

    def get_audit_trace(self, item_id: str, include_source_events: bool = False) -> dict:
        """Full lineage trace for any item."""
        # Determine item type
        event = self.db.get_event(item_id)
        fact = self.db.get_fact(item_id)

        trace: dict = {
            "item_id": item_id,
            "item_type": "event" if event else "fact" if fact else "unknown",
            "item_data": event or fact,
            "upstream": [],
            "downstream": [],
            "tombstones": self.db.get_tombstones(item_id),
        }

        # Upstream (parents)
        parents = self.db.get_parents(item_id)
        for p in parents:
            parent_data = self.db.get_event(p["parent_id"]) or self.db.get_fact(p["parent_id"])
            if p["parent_type"] == "event" and not include_source_events:
                parent_data = None
            trace["upstream"].append({
                "id": p["parent_id"],
                "type": p["parent_type"],
                "relation": p["relation"],
                "data": parent_data,
            })

        # Downstream (children)
        children = self.db.get_children(item_id)
        for c in children:
            child_data = self.db.get_fact(c["child_id"])
            trace["downstream"].append({
                "id": c["child_id"],
                "type": c["child_type"],
                "relation": c["relation"],
                "data": child_data,
            })

        return trace
