"""Personal health tracker demonstrating Lore's memory plus deletion verification."""

from __future__ import annotations

try:
    from lore.context_pack import ContextPackBuilder
    from lore.db import Database
    from lore.lineage import LineageEngine
    from lore.models import Event
except ImportError as exc:  # pragma: no cover - example guard
    raise SystemExit("Install lore first with `python -m pip install -e .`.") from exc


def main() -> None:
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    print("=== Personal Health Tracker ===\n")

    events = [
        Event(
            id="event:health:1",
            type="med_started",
            payload={"name": "metformin"},
            domains=["health"],
            sensitivity="high",
            metadata={"subject_id": "patient-alice"},
        ),
        Event(
            id="event:health:2",
            type="note",
            payload={"text": "Blood pressure reading 130/85, slightly elevated"},
            domains=["health"],
            sensitivity="medium",
            metadata={"subject_id": "patient-alice"},
        ),
        Event(
            id="event:health:3",
            type="note",
            payload={"text": "Allergic reaction to penicillin documented"},
            domains=["health"],
            sensitivity="medium",
            metadata={"subject_id": "patient-alice"},
        ),
    ]

    for event in events:
        db.insert_event(event)
        fact_ids = engine.derive_facts_for_event(db.get_event(event.id))
        print(f"Stored {event.id}: derived {len(fact_ids)} fact(s)")

    print("\n--- Retrieving health context ---")
    pack = builder.build(domain="health", query="penicillin medication", limit=10)
    print(f"Query returned {len(pack.facts)} fact(s)")
    for item in pack.facts:
        print(f"  - {item['key']}: {item['value']}")

    print("\n--- Deleting allergy record with proof ---")
    proof = engine.delete_and_recompute(
        "event:health:3", "event", reason="subject_erasure_request", mode="hard"
    )
    print(f"Deletion verified: {proof.to_dict().get('checks', {}).get('deletion_verified')}")

    print("\n--- Verifying erasure ---")
    pack_after = builder.build(domain="health", query="penicillin allergy", limit=10)
    print(f"Query after deletion: {len(pack_after.facts)} fact(s)")
    resurfaced = "penicillin" in str(pack_after.facts).lower()
    if not resurfaced:
        print("Deleted allergy content does not resurface.")
    else:
        print("WARNING: deleted allergy content is still visible.")


if __name__ == "__main__":
    main()
