"""Multi-agent shared memory demonstrating Lore's tenant isolation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Enable multi-tenant request semantics for the demo environment.
os.environ["LORE_ENABLE_MULTI_TENANT"] = "1"

from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.models import Edge, Event, Fact


def _seed_tenant_memory(
    db: Database,
    *,
    tenant_id: str,
    event_id: str,
    fact_id: str,
    key: str,
    text: str,
) -> None:
    event = Event(
        id=event_id,
        type="note",
        payload={"text": text},
        domains=["work"],
        sensitivity="medium",
        tenant_id=tenant_id,
    )
    db.insert_event(event)
    fact = Fact(
        id=fact_id,
        key=key,
        value={"text": text},
        version=1,
        rule_id="DemoSeedRule@v1",
        tenant_id=tenant_id,
    )
    db.insert_fact(fact)
    db.insert_edge(
        Edge(
            tenant_id=tenant_id,
            parent_id=event_id,
            parent_type="event",
            child_id=fact_id,
            child_type="fact",
        )
    )


def main() -> None:
    db = Database(":memory:")
    builder = ContextPackBuilder(db)

    print("=== Multi-Agent Shared Memory ===\n")

    _seed_tenant_memory(
        db,
        tenant_id="team-alpha",
        event_id="event:alpha:1",
        fact_id="fact:team-alpha:1",
        key="team_alpha_focus",
        text="Team Alpha is working on the payment gateway",
    )
    print("Agent A stored team-alpha memory about the payment gateway")

    _seed_tenant_memory(
        db,
        tenant_id="team-beta",
        event_id="event:beta:1",
        fact_id="fact:team-beta:1",
        key="team_beta_focus",
        text="Team Beta is migrating to Kubernetes",
    )
    print("Agent B stored team-beta memory about Kubernetes")

    print("\n--- Tenant isolation ---")
    pack_alpha = builder.build(domain="work", query="payment", tenant_id="team-alpha", limit=10)
    pack_beta = builder.build(domain="work", query="payment", tenant_id="team-beta", limit=10)
    pack_beta_own = builder.build(domain="work", query="kubernetes", tenant_id="team-beta", limit=10)

    alpha_text = " ".join(str(item["value"]) for item in pack_alpha.facts).lower()
    beta_payment_text = " ".join(str(item["value"]) for item in pack_beta.facts).lower()
    beta_own_text = " ".join(str(item["value"]) for item in pack_beta_own.facts).lower()

    print(f"Agent A query 'payment': {len(pack_alpha.facts)} fact(s)")
    print("Agent A sees payment gateway content:", "payment gateway" in alpha_text)
    print(f"Agent B query 'payment': {len(pack_beta.facts)} fact(s)")
    print("Agent B sees payment gateway content:", "payment gateway" in beta_payment_text)
    print(f"Agent B query 'kubernetes': {len(pack_beta_own.facts)} fact(s)")
    print("Agent B sees Kubernetes content:", "kubernetes" in beta_own_text)

    print("\nTenant isolation confirmed when one tenant cannot retrieve the other tenant's content.")


if __name__ == "__main__":
    main()
