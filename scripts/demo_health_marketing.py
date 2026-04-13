#!/usr/bin/env python3
"""Health-first marketing proof script for Orenyl."""

from __future__ import annotations

import sys
from typing import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Allow running the demo from a fresh checkout without editable install.
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from orenyl.db import Database
    from orenyl.lineage import LineageEngine
    from orenyl.models import Event
except ImportError as exc:  # pragma: no cover - script guard
    raise SystemExit("Unable to import Orenyl modules from the local src tree.") from exc

def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _sorted_strings(values: Iterable[object]) -> list[str]:
    return sorted(str(value) for value in values)


def _get_exact_current_fact(db: Database, key: str, expected_values: Iterable[object]) -> dict | None:
    expected = _sorted_strings(expected_values)
    for fact in db.get_current_facts(key=key):
        if _sorted_strings(fact["value"]) == expected:
            return fact
    return None


def _describe_med_started_event(event: Event) -> str:
    return f'Patient started {event.payload["name"]}'


def main() -> int:
    db = Database(":memory:")
    engine = LineageEngine(db)
    try:
        print("ORENYL: GOVERNED MEMORY PROOF")
        print("Governed memory for MCP agents")
        print("Vector stores remember. Orenyl governs.")

        events = [
            Event(
                id="event:marketing:health:1",
                type="med_started",
                payload={"name": "metformin"},
                domains=["health"],
                sensitivity="high",
                metadata={"subject_id": "patient-demo"},
            ),
            Event(
                id="event:marketing:health:2",
                type="med_started",
                payload={"name": "penicillin"},
                domains=["health"],
                sensitivity="high",
                metadata={"subject_id": "patient-demo"},
            ),
        ]

        for event in events:
            db.insert_event(event)
            engine.derive_facts_for_event(db.get_event(event.id))

        expected_sources = _sorted_strings(event.id for event in events)
        delete_target_event = events[-1]
        delete_target_label = _describe_med_started_event(delete_target_event)
        expected_before = _sorted_strings(event.payload["name"] for event in events)
        expected_after = _sorted_strings(
            event.payload["name"] for event in events if event.id != delete_target_event.id
        )

        print("\n=== Stored memory ===")
        for event in events:
            print(f'- "{_describe_med_started_event(event)}"')

        _print_header("Derived fact now")
        active_medications = _get_exact_current_fact(
            db,
            key="active_medications",
            expected_values=expected_before,
        )
        if active_medications is None:
            print("error: active_medications fact not returned", file=sys.stderr)
            return 1

        active_values_before = _sorted_strings(active_medications["value"])
        print(f"- Active medications: {', '.join(active_values_before)}")

        trace = engine.get_audit_trace(active_medications["id"], include_source_events=True)
        upstream_sources = _sorted_strings(
            item["id"]
            for item in trace["upstream"]
            if item["type"] == "event" and item["id"] in expected_sources
        )
        if upstream_sources != expected_sources:
            print("error: active_medications fact missing expected source events", file=sys.stderr)
            return 1

        _print_header("Audit trace")
        print(f"- Active medications <- {', '.join(upstream_sources)}")

        _print_header("Delete request")
        print(f'- Remove source memory: "{delete_target_label}"')

        proof = engine.delete_and_recompute(
            delete_target_event.id,
            "event",
            reason="demo_delete_request",
            mode="soft",
        )
        checks = proof.to_dict().get("checks", {})

        _print_header("Verification")
        print(f"deletion_verified: {checks.get('deletion_verified')}")
        print(f"resurfaced_references: {checks.get('resurfaced_references')}")

        _print_header("Facts after deletion")
        active_medications_after = _get_exact_current_fact(
            db,
            key="active_medications",
            expected_values=expected_after,
        )
        if active_medications_after is None:
            print("error: active_medications fact missing after deletion", file=sys.stderr)
            return 1

        active_values_after = _sorted_strings(active_medications_after["value"])
        print(f"- Active medications: {', '.join(active_values_after)}")
        penicillin_removed = "penicillin" not in active_values_after
        print(f"- Penicillin removed: {penicillin_removed}")

        if (
            checks.get("deletion_verified") is True
            and checks.get("resurfaced_references") == []
            and active_values_after == expected_after
            and penicillin_removed
        ):
            print("\nRESULT: deleted health content does not resurface.")
            return 0

        print("\nRESULT: verification failed.", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
