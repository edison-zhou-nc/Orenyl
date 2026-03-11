from lore.db import Database
from lore.models import Edge


def test_get_downstream_facts_uses_sql_recursive_cte(monkeypatch):
    db = Database(":memory:")
    db.insert_edge(Edge(parent_id="event:test:1", parent_type="event", child_id="fact:test:1"))
    db.insert_edge(Edge(parent_id="fact:test:1", parent_type="fact", child_id="fact:test:2"))

    def _fail_if_called(_):
        raise AssertionError("get_children should not be used")

    monkeypatch.setattr(db, "get_children", _fail_if_called)
    assert db.get_downstream_facts("event:test:1") == ["fact:test:1", "fact:test:2"]
