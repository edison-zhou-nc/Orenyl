from orenyl.semantic_dedup import check_semantic_duplicate


class _Provider:
    provider_id = "hash-local"

    def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0]


class _Db:
    def __init__(self):
        self.conn = None

    def get_recent_events_in_domains(self, domains, since_ts, tenant_id=""):
        return []


def test_check_semantic_duplicate_uses_database_api_not_raw_connection():
    db = _Db()
    is_dup, event_id = check_semantic_duplicate(
        db=db,
        provider=_Provider(),
        content="hello",
        domains=["health"],
    )
    assert is_dup is False
    assert event_id is None
