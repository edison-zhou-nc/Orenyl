"""Tests for dev-salt warning on startup."""

from __future__ import annotations

import base64
import logging
import os
from unittest import mock

from orenyl.encryption import _decode_salt


def test_decode_salt_logs_warning_when_insecure_dev_salt_used(caplog):
    """When LORE_ALLOW_INSECURE_DEV_SALT=1 and no salt is configured, a warning is logged."""
    env = {
        "LORE_ALLOW_INSECURE_DEV_SALT": "1",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("LORE_ENCRYPTION_SALT", None)
        with caplog.at_level(logging.WARNING, logger="orenyl.encryption"):
            result = _decode_salt("LORE_ENCRYPTION_SALT")

    assert len(result) >= 16
    assert result != b"orenyl-default-salt!"
    assert any("insecure" in record.message.lower() for record in caplog.records), (
        f"Expected WARNING about insecure salt, got: {[r.message for r in caplog.records]}"
    )


def test_decode_salt_no_warning_when_real_salt_configured(caplog):
    """When a real salt is configured, no warning is logged."""
    real_salt = base64.b64encode(b"production-salt-value!").decode("ascii")
    env = {"LORE_ENCRYPTION_SALT": real_salt}

    with mock.patch.dict(os.environ, env, clear=False):
        with caplog.at_level(logging.WARNING, logger="orenyl.encryption"):
            result = _decode_salt("LORE_ENCRYPTION_SALT")

    assert result == b"production-salt-value!"
    assert not any("insecure" in record.message.lower() for record in caplog.records)


def test_decode_salt_uses_process_local_fallback_not_static_literal(caplog):
    env = {
        "LORE_ALLOW_INSECURE_DEV_SALT": "1",
    }
    with mock.patch.dict(os.environ, env, clear=False):
        os.environ.pop("LORE_ENCRYPTION_SALT", None)
        with caplog.at_level(logging.WARNING, logger="orenyl.encryption"):
            first = _decode_salt("LORE_ENCRYPTION_SALT")
            second = _decode_salt("LORE_ENCRYPTION_SALT")

    assert first == second
    assert len(first) >= 16
    assert first != b"orenyl-default-salt!"
