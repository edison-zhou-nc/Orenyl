import asyncio

from lore.server import list_tools


def test_retrieve_description_mentions_memory_routing():
    tools = asyncio.run(list_tools())
    retrieve = next(t for t in tools if t.name == "retrieve_context_pack")
    desc = (retrieve.description or "").lower()
    assert "before using its own memory" in desc


def test_delete_description_mentions_soft_and_hard_modes():
    tools = asyncio.run(list_tools())
    delete = next(t for t in tools if t.name == "delete_and_recompute")
    desc = (delete.description or "").lower()
    assert "soft" in desc
    assert "hard" in desc

