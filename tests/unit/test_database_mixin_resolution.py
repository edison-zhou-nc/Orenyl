from lore.db import Database


def test_database_methods_come_from_mixins_not_class_body():
    expected_mixins = {
        "insert_event": "EventMixin",
        "get_current_facts": "FactMixin",
        "get_downstream_facts": "LineageMixin",
        "insert_tombstone": "ComplianceMixin",
        "append_sync_journal_entry": "FederationMixin",
        "upsert_event_embedding": "EmbeddingMixin",
        "log_retrieval": "AuditMixin",
    }

    for method_name, owner in expected_mixins.items():
        assert method_name not in Database.__dict__, f"{method_name} still defined on Database"
        assert getattr(Database, method_name).__qualname__.startswith(owner)
