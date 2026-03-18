"""Meeting memory demonstrating Lore's lineage tracking and cascade deletion."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event


def main() -> None:
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    print("=== Meeting Memory ===\n")

    meetings = [
        Event(
            id="event:meeting:standup-mon",
            type="note",
            payload={"text": "Monday standup: API redesign approved, deadline is March 30"},
            domains=["work"],
            sensitivity="low",
        ),
        Event(
            id="event:meeting:design-review",
            type="note",
            payload={"text": "Design review: chose PostgreSQL over DynamoDB for the new service"},
            domains=["work"],
            sensitivity="low",
        ),
    ]

    for event in meetings:
        db.insert_event(event)
        fact_ids = engine.derive_facts_for_event(db.get_event(event.id))
        print(f"Meeting {event.id}: derived {len(fact_ids)} fact(s)")

    print("\n--- Retrieving work context ---")
    pack = builder.build(domain="work", query="API deadline", limit=10)
    print(f"Found {len(pack.facts)} relevant fact(s)")
    summary_item = next((item for item in pack.facts if item["key"] == "domain_summary"), None)

    print("\n--- Lineage trace ---")
    if summary_item is not None:
        print(f"Summary before deletion: {summary_item['value']}")
        sources = summary_item.get("provenance", {}).get("derived_from", [])
        print(f"Summary derived from: {sources}")
    else:
        print(
            "No domain_summary fact found. This demo expects note-based events, "
            "because the lineage walkthrough traces the domain_summary rule."
        )

    print("\n--- Deleting Monday standup ---")
    proof = engine.delete_and_recompute(
        "event:meeting:standup-mon", "event", reason="retention_policy", mode="soft"
    )
    print(f"Deletion verified: {proof.to_dict().get('checks', {}).get('deletion_verified')}")

    pack_after = builder.build(domain="work", query="API deadline", limit=10)
    summary_after = next((item for item in pack_after.facts if item["key"] == "domain_summary"), None)
    if summary_after is not None:
        print(f"Summary after deletion: {summary_after['value']}")
        print(
            "Deleted meeting removed from summary:",
            "march 30" not in str(summary_after["value"]).lower(),
        )
    else:
        print(
            "No domain_summary fact found after deletion. This usually means the demo "
            "events did not hit the note-based summary path."
        )


if __name__ == "__main__":
    main()
