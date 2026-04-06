import asyncio

import pytest

from orenyl import server
from orenyl.context_pack import ContextPackBuilder
from orenyl.db import Database
from orenyl.lineage import LineageEngine


def _reset_server_state(monkeypatch):
    fresh_db = Database(":memory:")
    monkeypatch.setattr(server, "db", fresh_db)
    monkeypatch.setattr(server, "engine", LineageEngine(fresh_db))
    monkeypatch.setattr(server, "pack_builder", ContextPackBuilder(fresh_db))


def test_restricted_encryption_refuses_static_default_salt_in_prod(monkeypatch):
    _reset_server_state(monkeypatch)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "top-secret-passphrase")
    monkeypatch.delenv("LORE_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LORE_ALLOW_INSECURE_DEV_SALT", raising=False)

    with pytest.raises(RuntimeError, match="LORE_ENCRYPTION_SALT is required"):
        asyncio.run(
            server.handle_store_event(
                {
                    "domains": ["health"],
                    "type": "diet_preference",
                    "payload": {"value": "vegan"},
                    "sensitivity": "restricted",
                }
            )
        )


def test_missing_salt_is_error_when_passphrase_set_in_prod(monkeypatch):
    _reset_server_state(monkeypatch)
    monkeypatch.setenv("LORE_ENCRYPTION_PASSPHRASE", "top-secret-passphrase")
    monkeypatch.delenv("LORE_ENCRYPTION_SALT", raising=False)
    monkeypatch.delenv("LORE_ALLOW_INSECURE_DEV_SALT", raising=False)

    with pytest.raises(RuntimeError, match="LORE_ENCRYPTION_SALT is required"):
        asyncio.run(
            server.handle_store_event(
                {
                    "domains": ["general"],
                    "type": "note",
                    "payload": {"text": "sensitive"},
                    "sensitivity": "high",
                }
            )
        )
