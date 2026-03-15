"""Shared helpers used by extracted server handlers."""

from __future__ import annotations

import base64
import json
import os
import uuid
from typing import Any

from ..encryption import resolve_runtime_keyring


def _resolve_request_id(args: dict[str, Any]) -> str:
    request_id = str(args.get("_request_id", "")).strip()
    if request_id:
        return request_id
    return f"req:{uuid.uuid4().hex[:12]}"


def _clamp_positive_int(value: Any, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return 1
    if parsed > maximum:
        return maximum
    return parsed


def _clamp_non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _encode_cursor(created_at: str, item_id: str) -> str:
    raw = json.dumps({"created_at": created_at, "id": item_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
        return str(payload["created_at"]), str(payload["id"])
    except Exception as exc:
        raise ValueError("invalid_cursor") from exc


def _build_export_items(events: list[dict], facts: list[dict]) -> list[dict]:
    items: list[dict] = []
    for ev in events:
        items.append(
            {
                "id": ev["id"],
                "kind": "event",
                "created_at": ev.get("created_at", ""),
                "ts": ev.get("ts", ""),
                "domain_hint": ev.get("domains", []),
                "data": ev,
            }
        )
    for fact in facts:
        items.append(
            {
                "id": fact["id"],
                "kind": "fact",
                "created_at": fact.get("created_at", ""),
                "key": fact.get("key", ""),
                "data": fact,
            }
        )
    items.sort(key=lambda item: (item.get("created_at", ""), item["id"]))
    return items


def _runtime_encryption_material() -> tuple[bytes, bytes, str] | None:
    has_legacy = bool(os.environ.get("LORE_ENCRYPTION_PASSPHRASE", "").strip())
    has_versioned = any(key.startswith("LORE_ENCRYPTION_PASSPHRASE_") for key in os.environ)
    if not has_legacy and not has_versioned:
        return None
    keyring = resolve_runtime_keyring()
    selected = keyring.keys[keyring.active_version]
    return selected.key, selected.salt, keyring.active_version
