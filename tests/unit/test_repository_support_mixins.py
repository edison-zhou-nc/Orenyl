from lore.repositories.audit import AuditMixin
from lore.repositories.embeddings import EmbeddingMixin
from lore.repositories.federation import FederationMixin


def test_support_mixins_cover_remaining_database_api():
    assert {
        "append_sync_journal_entry",
        "list_sync_journal_entries",
        "update_sync_journal_status",
        "sync_journal_count",
    } <= set(dir(FederationMixin))
    assert {
        "upsert_event_embedding",
        "get_event_embedding",
        "upsert_fact_embedding",
        "get_fact_embeddings",
    } <= set(dir(EmbeddingMixin))
    assert {"log_retrieval", "get_retrieval_logs"} <= set(dir(AuditMixin))
