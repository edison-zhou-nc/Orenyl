import pytest

from orenyl.embedding_provider import build_embedding_provider_from_env


def test_openai_provider_warns_when_embedding_dim_env_set(monkeypatch, caplog):
    caplog.set_level("WARNING")
    monkeypatch.setenv("ORENYL_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("ORENYL_OPENAI_API_KEY", "k")
    monkeypatch.setenv("ORENYL_EMBEDDING_DIM", "1536")

    _ = build_embedding_provider_from_env()

    assert any("ORENYL_EMBEDDING_DIM" in record.message for record in caplog.records)


def test_build_embedding_provider_rejects_legacy_env_vars(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("LORE_EMBEDDING_PROVIDER", "openai")

        with pytest.raises(RuntimeError, match="LORE_EMBEDDING_PROVIDER"):
            build_embedding_provider_from_env()
