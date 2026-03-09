from lore.db import Database
from lore.context_pack import ContextPackBuilder


def test_context_pack_has_v2_shape():
    db = Database(":memory:")
    pack = ContextPackBuilder(db).build(query="", limit=20)
    data = pack.to_dict()
    assert "domain" in data
    assert "event_count" in data
    assert "drill_down_available" in data


def test_context_pack_facts_and_items_are_distinct_lists():
    db = Database(":memory:")
    pack = ContextPackBuilder(db).build(query="", limit=20)
    assert pack.facts is not pack.items
