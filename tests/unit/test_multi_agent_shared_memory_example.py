"""Tests for the multi-agent shared memory example script."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_example_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "multi-agent-shared-memory"
        / "shared_memory.py"
    )
    spec = importlib.util.spec_from_file_location("shared_memory_example", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakePack:
    def __init__(self, facts):
        self.facts = facts


def test_shared_memory_example_returns_nonzero_when_isolation_fails(monkeypatch):
    module = _load_example_module()

    class FailingBuilder:
        def __init__(self, db):
            self._db = db

        def build(self, *, domain, query, tenant_id, limit):
            if tenant_id == "team-alpha":
                return _FakePack([{"value": {"text": "payment gateway"}}])
            if query == "payment":
                return _FakePack([{"value": {"text": "payment gateway"}}])
            return _FakePack([{"value": {"text": "kubernetes"}}])

    monkeypatch.setattr(module, "ContextPackBuilder", FailingBuilder)

    assert module.main() == 1
