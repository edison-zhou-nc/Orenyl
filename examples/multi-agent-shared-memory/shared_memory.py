"""Multi-agent shared memory demonstrating Lore's tenant isolation."""

from __future__ import annotations

import os
import sys

try:
    from lore.context_pack import ContextPackBuilder
    from lore.db import Database
    from lore.models import Edge, Event, Fact
except ImportError as exc:  # pragma: no cover - example guard
    raise SystemExit("Install lore first with `python -m pip install -e .`.") from exc


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


def main() -> int:
    previous_multi_tenant = os.environ.get("LORE_ENABLE_MULTI_TENANT")
    os.environ["LORE_ENABLE_MULTI_TENANT"] = "1"
    try:
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
        pack_alpha = builder.build(
            domain="work",
            query="payment",
            tenant_id="team-alpha",
            limit=10,
        )
        pack_beta = builder.build(
            domain="work",
            query="payment",
            tenant_id="team-beta",
            limit=10,
        )
        pack_beta_own = builder.build(
            domain="work",
            query="kubernetes",
            tenant_id="team-beta",
            limit=10,
        )

        alpha_text = " ".join(str(item["value"]) for item in pack_alpha.facts).lower()
        beta_payment_text = " ".join(str(item["value"]) for item in pack_beta.facts).lower()
        beta_own_text = " ".join(str(item["value"]) for item in pack_beta_own.facts).lower()

        print(f"Agent A query 'payment': {len(pack_alpha.facts)} fact(s)")
        print("Agent A sees payment gateway content:", "payment gateway" in alpha_text)
        print(f"Agent B query 'payment': {len(pack_beta.facts)} fact(s)")
        print("Agent B sees payment gateway content:", "payment gateway" in beta_payment_text)
        print(f"Agent B query 'kubernetes': {len(pack_beta_own.facts)} fact(s)")
        print("Agent B sees Kubernetes content:", "kubernetes" in beta_own_text)

        alpha_ok = "payment gateway" in alpha_text
        beta_isolated = "payment gateway" not in beta_payment_text
        beta_ok = "kubernetes" in beta_own_text
        if alpha_ok and beta_isolated and beta_ok:
            print(
                "\nTenant isolation confirmed when one tenant cannot retrieve "
                "the other tenant's content."
            )
            return 0

        print(
            "\nERROR: tenant isolation demo did not produce the expected isolation evidence.",
            file=sys.stderr,
        )
        return 1
    finally:
        if previous_multi_tenant is None:
            os.environ.pop("LORE_ENABLE_MULTI_TENANT", None)
        else:
            os.environ["LORE_ENABLE_MULTI_TENANT"] = previous_multi_tenant


if __name__ == "__main__":
    raise SystemExit(main())
