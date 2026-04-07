"""Two-minute orenyl v2 demo script for OpenClaw/distribution walkthrough."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine
from orenyl.models import Event


def main() -> None:
    db = Database(":memory:")
    engine = LineageEngine(db)
    builder = ContextPackBuilder(db)

    event = Event(
        id="event:demo:1",
        type="note",
        payload={"text": "Started metformin and sleeping better"},
        domains=["health"],
        sensitivity="medium",
    )
    db.insert_event(event)
    derived = engine.derive_facts_for_event(db.get_event(event.id))

    pack = builder.build(domain="health", include_summary=True, max_sensitivity="high", limit=10)
    proof = engine.delete_and_recompute(event.id, "event", reason="demo_cleanup", mode="soft")

    print("Derived facts:", derived)
    print("Context facts:", len(pack.to_dict().get("facts", [])))
    print("Deletion verified:", proof.to_dict().get("checks", {}).get("deletion_verified"))


if __name__ == "__main__":
    main()
