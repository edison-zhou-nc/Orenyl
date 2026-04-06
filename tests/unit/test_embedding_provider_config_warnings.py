from orenyl.embedding_provider import build_embedding_provider_from_env


def test_openai_provider_warns_when_embedding_dim_env_set(monkeypatch, caplog):
    caplog.set_level("WARNING")
    monkeypatch.setenv("ORENYL_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("ORENYL_OPENAI_API_KEY", "k")
    monkeypatch.setenv("ORENYL_EMBEDDING_DIM", "1536")

    _ = build_embedding_provider_from_env()

    assert any("ORENYL_EMBEDDING_DIM" in record.message for record in caplog.records)
