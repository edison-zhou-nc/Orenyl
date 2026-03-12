"""Data models for Lore governed memory."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(prefix: str, subtype: str = "") -> str:
    short = uuid.uuid4().hex[:12]
    if subtype:
        return f"{prefix}:{subtype}:{short}"
    return f"{prefix}:{short}"


@dataclass
class Event:
    id: str
    type: str
    payload: dict[str, Any]
    domains: list[str] = field(default_factory=list)
    content_hash: str | None = None
    sensitivity: str = "medium"
    consent_source: str = "implicit"
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "user"
    tenant_id: str = "default"
    ts: str = ""
    valid_from: str | None = None
    valid_to: str | None = None
    created_at: str = ""
    deleted_at: str | None = None

    def __post_init__(self):
        if not self.ts:
            self.ts = now_iso()
        if not self.created_at:
            self.created_at = now_iso()


@dataclass
class Fact:
    id: str
    key: str
    value: Any
    transform_config: dict[str, Any] = field(default_factory=dict)
    stale: bool = False
    importance: float = 0.5
    version: int = 1
    rule_id: str = ""
    rule_version: str = ""
    confidence: float = 1.0
    model_id: str = "deterministic"
    tenant_id: str = "default"
    valid_from: str = ""
    valid_to: str | None = None
    created_at: str = ""
    invalidated_at: str | None = None
    invalidation_reason: str | None = None

    def __post_init__(self):
        if not self.valid_from:
            self.valid_from = now_iso()
        if not self.created_at:
            self.created_at = now_iso()
        if not self.rule_version:
            if "@" in self.rule_id:
                self.rule_version = self.rule_id.split("@", 1)[1]
            else:
                self.rule_version = "v1"


@dataclass
class Edge:
    parent_id: str
    parent_type: str  # "event" or "fact"
    child_id: str
    tenant_id: str = "default"
    child_type: str = "fact"
    relation: str = "derived_from"


@dataclass
class Tombstone:
    target_id: str
    target_type: str
    tenant_id: str = "default"
    reason: str = ""
    deleted_at: str = ""
    cascade_invalidated: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.deleted_at:
            self.deleted_at = now_iso()


@dataclass
class RecallTrace:
    query: str
    included: list[dict[str, Any]] = field(default_factory=list)

    def add_item(self, item_id: str, why: list[str], lineage: list[str] | None = None):
        self.included.append({
            "item_id": item_id,
            "why": why,
            "lineage": lineage or [],
            "lineage_available": True,
        })


@dataclass
class ContextPack:
    schema_version: str = "0.2"
    generated_at: str = ""
    subject: dict[str, str] = field(default_factory=lambda: {"id": "user:default"})
    domain: str = "general"
    event_count: int = 0
    latest_event: str | None = None
    drill_down_available: bool = False
    facts: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = now_iso()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class DeleteProof:
    """The killer artifact: proof that deletion propagated correctly."""
    target_id: str
    target_type: str
    reason: str
    tombstoned: list[str] = field(default_factory=list)
    invalidated_facts: list[str] = field(default_factory=list)
    rederived_facts: list[dict[str, Any]] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    post_delete_check: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.checks and self.post_delete_check:
            self.checks = dict(self.post_delete_check)
        elif self.checks and not self.post_delete_check:
            self.post_delete_check = dict(self.checks)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
