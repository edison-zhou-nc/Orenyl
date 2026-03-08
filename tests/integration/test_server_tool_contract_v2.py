import asyncio
from lore.server import list_tools


def test_server_exposes_6_v2_tools():
    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert names == {
        "store_event",
        "retrieve_context_pack",
        "delete_and_recompute",
        "audit_trace",
        "list_events",
        "export_domain",
    }

