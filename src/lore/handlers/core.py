"""Core MCP tool handlers extracted from server.py."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time

from mcp.types import TextContent

from .. import __version__ as lore_version
from .. import audit, env_vars
from ..auth import authorize_action
from ..config import (
    multi_tenant_enabled,
    semantic_dedup_threshold_for_domains,
)
from ..content_hash import check_duplicate, compute_content_hash
from ..context_pack import backfill_missing_fact_embeddings
from ..encryption import encrypt_content
from ..metrics import inc_tool_call, observe_latency, render_prometheus
from ..models import Event, new_id, now_iso
from ..noise_filter import contains_sensitive_identifier, should_store
from ..query_understanding import infer_domain, rewrite_query
from ..semantic_dedup import check_semantic_duplicate
from ._common import (
    _build_export_items,
    _clamp_non_negative_int,
    _clamp_positive_int,
    _decode_cursor,
    _encode_cursor,
    _runtime_encryption_material,
)
from ._deps import (
    get_db,
    get_embedding_provider,
    get_engine,
    get_max_context_pack_limit,
    get_max_list_events_limit,
    get_pack_builder,
    get_transport_mode,
)

logger = logging.getLogger(__name__)
ALLOWED_SENSITIVITY_LEVELS = {"low", "medium", "high", "restricted"}


def _subject_id_for_event(event: dict | None) -> str:
    return str((event or {}).get("metadata", {}).get("subject_id", "")).strip()


async def handle_store_event(args: dict) -> list[TextContent]:
    started = time.perf_counter()
    db = get_db()
    engine = get_engine()
    payload = args.get("payload", {})
    content = args.get("content", "")
    if content and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("text", content)
    content_basis = content or json.dumps(payload, sort_keys=True)
    filter_target = content
    if filter_target:
        should_accept, reject_reason = should_store(filter_target)
        if not should_accept:
            logger.info(
                "store_event_rejected request_id=%s reason=%s domains=%s",
                args.get("_request_id", ""),
                reject_reason,
                args.get("domains", ["general"]),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"stored": False, "reason": reject_reason}, indent=2),
                )
            ]
    elif contains_sensitive_identifier(content_basis):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"stored": False, "reason": "sensitive_credential_or_identifier"},
                    indent=2,
                ),
            )
        ]
    content_hash = compute_content_hash(content_basis)
    domains = args.get("domains", ["general"])
    tenant_id = args.get("_auth_tenant_id", "")
    if check_duplicate(db, content_hash, domains, window_hours=24, tenant_id=tenant_id):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "stored": False,
                        "duplicate": True,
                        "content_hash": content_hash,
                        "reason": "duplicate_within_24h",
                    },
                    indent=2,
                ),
            )
        ]
    enable_semantic_dedup = os.environ.get(env_vars.ENABLE_SEMANTIC_DEDUP, "0") == "1"
    if enable_semantic_dedup:
        provider = get_embedding_provider()
        is_dup, existing_event_id = check_semantic_duplicate(
            db,
            provider,
            content_basis,
            domains,
            window_hours=24,
            threshold=semantic_dedup_threshold_for_domains(domains),
            tenant_id=tenant_id,
        )
        if is_dup:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "stored": False,
                            "duplicate": True,
                            "content_hash": content_hash,
                            "reason": "semantic_duplicate_within_24h",
                            "existing_event_id": existing_event_id,
                        },
                        indent=2,
                    ),
                )
            ]
    sensitivity = args.get("sensitivity", "medium")
    if str(sensitivity or "").lower() not in ALLOWED_SENSITIVITY_LEVELS:
        return [
            TextContent(
                type="text",
                text=json.dumps({"stored": False, "reason": "invalid_sensitivity"}, indent=2),
            )
        ]
    plain_payload = payload
    encryption_material = _runtime_encryption_material()
    should_encrypt_payload = (
        sensitivity in {"high", "restricted"} and encryption_material is not None
    )
    event_payload = plain_payload
    if should_encrypt_payload:
        assert encryption_material is not None
        runtime_key, runtime_salt, key_version = encryption_material
        plaintext = content or json.dumps(plain_payload, sort_keys=True)
        event_payload = {
            "_encrypted": True,
            "ciphertext": encrypt_content(
                plaintext,
                runtime_key,
                salt=runtime_salt,
                key_version=key_version,
            ),
        }

    event = Event(
        id=new_id("event", args.get("type", "note")),
        type=args.get("type", "note"),
        payload=event_payload,
        domains=domains,
        content_hash=content_hash,
        sensitivity=sensitivity,
        consent_source=args.get("consent_source", "implicit"),
        expires_at=args.get("expires_at"),
        metadata={
            **(args.get("metadata", {}) or {}),
            "tenant_id": args.get("_auth_tenant_id", "default"),
        },
        source=args.get("source", "user"),
        tenant_id=args.get("_auth_tenant_id", "default"),
        ts=args.get("ts", now_iso()),
    )

    db.insert_event(event)
    try:
        provider = get_embedding_provider()
        event_embedding = provider.embed_text(content_basis)
        db.upsert_event_embedding(
            event.id,
            event_embedding,
            provider.provider_id,
            tenant_id=tenant_id or "default",
        )
    except Exception as exc:
        logger.warning("event_embedding_index_failed event_id=%s error=%s", event.id, exc)
    derived_fact_ids = (
        [] if should_encrypt_payload else engine.derive_facts_for_event(db.get_event(event.id))
    )
    if derived_fact_ids:
        try:
            backfill_missing_fact_embeddings(
                db,
                derived_fact_ids,
                tenant_id=args.get("_auth_tenant_id", ""),
            )
        except Exception as exc:
            logger.warning("fact_embedding_backfill_failed event_id=%s error=%s", event.id, exc)

    result = {
        "stored": True,
        "event_id": event.id,
        "type": event.type,
        "payload": {"_encrypted": True} if should_encrypt_payload else event.payload,
        "domains": event.domains,
        "ts": event.ts,
        "derived_facts": derived_fact_ids,
    }
    logger.info(
        "store_event_success request_id=%s event_id=%s domains=%s sensitivity=%s",
        args.get("_request_id", ""),
        event.id,
        event.domains,
        sensitivity,
    )
    observe_latency("store_event_latency_ms", (time.perf_counter() - started) * 1000.0)
    inc_tool_call("store_event", "ok")
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_retrieve_context_pack(args: dict) -> list[TextContent]:
    started = time.perf_counter()
    domain = args.get("domain", "general")
    query = args.get("query", "")
    rewritten_query = rewrite_query(query)
    if domain == "general" and rewritten_query:
        domain = infer_domain(rewritten_query, fallback="general")
    limit = _clamp_positive_int(
        args.get("limit", 50), default=50, maximum=get_max_context_pack_limit()
    )
    pack = get_pack_builder().build(
        domain=domain,
        include_summary=args.get("include_summary", True),
        max_sensitivity=args.get("max_sensitivity", "high"),
        limit=limit,
        query=rewritten_query,
        tenant_id=args.get("_auth_tenant_id", ""),
        agent_id=args.get("agent_id", ""),
        session_id=args.get("session_id", ""),
    )
    pack_json = pack.to_json()
    logger.info(
        "retrieve_context_pack request_id=%s domain=%s limit=%s",
        args.get("_request_id", ""),
        domain,
        limit,
    )
    observe_latency("context_pack_latency_ms", (time.perf_counter() - started) * 1000.0)
    inc_tool_call("retrieve_context_pack", "ok")
    return [TextContent(type="text", text=pack_json)]


async def handle_metrics(args: dict) -> list[TextContent]:
    """Internal-only diagnostic endpoint that is not dispatched as an MCP tool."""
    return [TextContent(type="text", text=render_prometheus())]


async def handle_health(args: dict) -> list[TextContent]:
    """Internal-only diagnostic endpoint that is not dispatched as an MCP tool."""
    db_ok = get_db().ping()
    try:
        encryption_enabled = _runtime_encryption_material() is not None
    except Exception:
        encryption_enabled = False
    payload = {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "version": lore_version,
        "transport": get_transport_mode(),
        "multi_tenant_enabled": multi_tenant_enabled(),
        "encryption_enabled": encryption_enabled,
    }
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def handle_audit_trace(args: dict) -> list[TextContent]:
    trace = get_engine().get_audit_trace(
        args["item_id"],
        include_source_events=args.get("include_source_events", False),
        tenant_id=args.get("_auth_tenant_id", ""),
    )
    logger.info(
        "audit_trace request_id=%s item_id=%s include_source_events=%s",
        args.get("_request_id", ""),
        args["item_id"],
        args.get("include_source_events", False),
    )
    return [TextContent(type="text", text=json.dumps(trace, indent=2, default=str))]


async def handle_delete_and_recompute(args: dict) -> list[TextContent]:
    engine = get_engine()
    request_id = str(args.get("_request_id", ""))
    principal_id = str(args.get("_auth_client_id", ""))
    target_id = args["target_id"]
    target_type = args["target_type"]
    mode = args.get("mode", "soft")
    audit_result = "error"
    audit_details = {"target_id": target_id, "target_type": target_type, "mode": mode}
    try:
        proof = engine.delete_and_recompute(
            target_id=target_id,
            target_type=target_type,
            reason=args.get("reason", ""),
            mode=mode,
            run_vacuum=args.get("run_vacuum", False),
            tenant_id=args.get("_auth_tenant_id", ""),
        )
        proof_json = proof.to_json()
        audit_result = "allow"
        return [TextContent(type="text", text=proof_json)]
    finally:
        audit.log_security_event(
            "delete_and_recompute",
            audit_result,
            principal_id=principal_id,
            request_id=request_id,
            details=audit_details,
        )
        logger.info(
            "delete_and_recompute request_id=%s target_id=%s target_type=%s mode=%s result=%s",
            request_id,
            target_id,
            target_type,
            mode,
            audit_result,
        )


async def handle_list_events(args: dict) -> list[TextContent]:
    db = get_db()
    domain = args.get("domain", "general")
    include_tombstoned = args.get("include_tombstoned", False)
    offset = _clamp_non_negative_int(args.get("offset", 0), default=0)
    limit = _clamp_positive_int(
        args.get("limit", 50), default=50, maximum=get_max_list_events_limit()
    )
    domain_filter = [] if domain == "general" else [domain]
    tenant_id = args.get("_auth_tenant_id", "")
    total_count = db.count_events_by_domains(
        domain_filter,
        include_tombstoned=include_tombstoned,
        tenant_id=tenant_id,
    )
    window = db.list_events_page(
        domains=domain_filter,
        include_tombstoned=include_tombstoned,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
    )
    logger.info(
        "list_events request_id=%s domain=%s offset=%s limit=%s include_tombstoned=%s",
        args.get("_request_id", ""),
        domain,
        offset,
        limit,
        include_tombstoned,
    )
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {"total_count": total_count, "count": len(window), "events": window},
                indent=2,
            ),
        )
    ]


async def handle_export_domain(args: dict) -> list[TextContent]:
    db = get_db()
    domain = args.get("domain", "general")
    fmt = args.get("format", "json")
    page_size = _clamp_non_negative_int(args.get("page_size", 0), default=0)
    stream_mode = bool(args.get("stream", False))
    include_hashes = bool(args.get("include_hashes", False))
    cursor = str(args.get("cursor", "")).strip()
    tenant_id = args.get("_auth_tenant_id", "")
    restricted = db.get_restricted_fact_ids_for_export_domain(domain, tenant_id=tenant_id)

    auth_scopes = args.get("_auth_scopes") or []
    if restricted:
        try:
            authorize_action(set(auth_scopes), "export_domain", restricted=True)
        except PermissionError as exc:
            audit.log_security_event(
                "export_domain",
                "deny",
                principal_id=str(args.get("_auth_client_id", "")),
                request_id=str(args.get("_request_id", "")),
                details={"reason": "forbidden", "error": str(exc)},
            )
            raise PermissionError(f"forbidden:{exc}") from exc
    if restricted and not args.get("confirm_restricted", False):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "restricted_data_requires_confirmation",
                        "restricted_fact_ids": restricted,
                    },
                    indent=2,
                ),
            )
        ]

    if page_size > 0 or cursor or stream_mode:
        event_count = db.get_event_count(domain=domain, tenant_id=tenant_id)
        if event_count > 10_000:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": "export_domain_too_large_for_pagination",
                            "event_count": event_count,
                        },
                        indent=2,
                    ),
                )
            ]

    events = (
        db.get_active_events_by_domains([domain], tenant_id=tenant_id)
        if domain != "general"
        else db.get_active_events(tenant_id=tenant_id)
    )
    facts = db.get_current_facts_by_domain(domain, tenant_id=tenant_id)
    fact_ids = [fact["id"] for fact in facts]
    parents_by_fact = db.get_parents_for_children(fact_ids, tenant_id=tenant_id)

    event_ids = {ev["id"] for ev in events}
    edges = []
    for fact in facts:
        for parent in parents_by_fact.get(fact["id"], []):
            if parent.get("parent_type") != "event":
                continue
            if domain != "general" and parent.get("parent_id") not in event_ids:
                continue
            edges.append(
                {"from": parent["parent_id"], "to": fact["id"], "relation": parent["relation"]}
            )

    payload = {
        "domain": domain,
        "events": events,
        "facts": facts,
        "edges": edges,
        "summary": f"events={len(events)}, facts={len(facts)}, edges={len(edges)}",
    }
    logger.info(
        "export_domain request_id=%s domain=%s format=%s",
        args.get("_request_id", ""),
        domain,
        fmt,
    )
    if page_size > 0 or cursor or stream_mode:
        items = _build_export_items(events, facts)
        if cursor:
            try:
                cursor_key = _decode_cursor(cursor)
            except ValueError:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "invalid_cursor"}, indent=2),
                    )
                ]
            items = [item for item in items if (item["created_at"], item["id"]) > cursor_key]
        window = items[:page_size] if page_size > 0 else items
        has_more = page_size > 0 and len(items) > len(window)
        next_cursor = ""
        if has_more and window:
            tail = window[-1]
            next_cursor = _encode_cursor(tail["created_at"], tail["id"])
        page_payload = {
            "domain": domain,
            "items": window,
            "count": len(window),
            "has_more": has_more,
            "next_cursor": next_cursor,
        }
        if stream_mode:
            lines = [
                json.dumps({"kind": "record", "item": item}, separators=(",", ":"))
                for item in window
            ]
            if include_hashes:
                canonical = "\n".join(
                    json.dumps(item, sort_keys=True, separators=(",", ":")) for item in window
                )
                lines.append(
                    json.dumps(
                        {
                            "kind": "chunk_hash",
                            "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                        },
                        separators=(",", ":"),
                    )
                )
            lines.append(
                json.dumps(
                    {
                        "kind": "page_info",
                        "count": len(window),
                        "has_more": has_more,
                        "next_cursor": next_cursor,
                    },
                    separators=(",", ":"),
                )
            )
            return [TextContent(type="text", text="\n".join(lines))]
        return [TextContent(type="text", text=json.dumps(page_payload, indent=2, default=str))]

    if fmt == "markdown":
        lines = [f"# Domain Export: {domain}", "", "## Events"]
        for ev in events:
            lines.append(f"- `{ev['id']}` {ev['ts']} {ev['type']}")
        lines.append("")
        lines.append("## Facts")
        for fact in facts:
            lines.append(f"- `{fact['id']}` key={fact['key']}")
        lines.append("")
        lines.append("## Summary")
        lines.append(payload["summary"])
        return [TextContent(type="text", text="\n".join(lines))]
    if fmt == "timeline":
        ordered = sorted(events, key=lambda e: e.get("ts", ""))
        lines = [f"Timeline export for domain: {domain}"]
        for ev in ordered:
            lines.append(f"{ev['ts']} - {ev['type']} ({ev['id']})")
        lines.append("")
        lines.append(payload["summary"])
        return [TextContent(type="text", text="\n".join(lines))]
    return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]
