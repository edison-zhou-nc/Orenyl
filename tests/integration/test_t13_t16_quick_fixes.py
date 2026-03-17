import asyncio
import subprocess
import sys

from lore.context_pack import ContextPackBuilder
from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event
from lore.server import list_tools


def test_retrieve_context_pack_schema_includes_query():
    tools = asyncio.run(list_tools())
    retrieve = next(t for t in tools if t.name == "retrieve_context_pack")
    assert "query" in retrieve.inputSchema.get("properties", {})


def test_context_pack_build_domain_scopes_fact_selection():
    db = Database(":memory:")
    engine = LineageEngine(db)

    e1 = Event(
        id="event:test:h", type="med_started", payload={"name": "metformin"}, domains=["health"]
    )
    e2 = Event(
        id="event:test:c",
        type="role_assigned",
        payload={"user": "u", "role": "admin"},
        domains=["career"],
    )
    db.insert_event(e1)
    db.insert_event(e2)
    engine.derive_facts_for_event(db.get_event(e1.id))
    engine.derive_facts_for_event(db.get_event(e2.id))

    pack = ContextPackBuilder(db).build(domain="health", query="what do you remember")
    keys = {f["key"] for f in pack.to_dict().get("facts", [])}
    assert "active_medications" in keys
    assert "current_role" not in keys


def test_demo_script_runs_from_repo_root():
    proc = subprocess.run(
        [sys.executable, "scripts/demo_v2.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
