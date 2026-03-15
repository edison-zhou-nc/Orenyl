"""Lore Governed Memory MCP Server."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import threading
import time
from typing import Any

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import audit
from .article30 import generate_article30_report
from .audit_anomaly import scan_access_anomalies
from .auth import (
    OIDCTokenVerifier,
    authorize_action,
    build_token_verifier_from_env,
    extract_auth_token,
)
from .compliance import ComplianceService
from .config import read_only_mode_enabled, semantic_dedup_threshold_for_domains
from .consent import ConsentService
from .content_hash import check_duplicate, compute_content_hash
from .context_pack import ContextPackBuilder, backfill_missing_fact_embeddings
from .context_pack import (
    _reset_runtime_state_for_tests as reset_context_pack_runtime_state_for_tests,
)
from .db import Database
from .disaster_recovery import DRService
from .embedding_provider import build_embedding_provider_from_env
from .encryption import encrypt_content
from .federation_worker import FederationWorker
from .handlers._common import (
    _build_export_items,
    _clamp_non_negative_int,
    _clamp_positive_int,
    _decode_cursor,
    _encode_cursor,
    _resolve_request_id,
    _runtime_encryption_material,
)
from .lineage import LineageEngine
from .metrics import inc_tool_call, observe_latency, render_prometheus, reset_metrics_for_tests
from .models import Event, new_id, now_iso
from .noise_filter import contains_sensitive_identifier, should_store
from .policy import (
    PolicyEngine,
    agent_permissions_enabled,
    policy_shadow_mode_enabled,
)
from .query_understanding import infer_domain, rewrite_query
from .semantic_dedup import check_semantic_duplicate
from .tenant import (
    reset_current_tenant_context,
    resolve_tenant_context,
    set_current_tenant_context,
)

DB_PATH = os.environ.get("LORE_DB_PATH", "lore_memory.db")
MAX_CONTEXT_PACK_LIMIT = int(os.environ.get("LORE_MAX_CONTEXT_PACK_LIMIT", "100"))
MAX_LIST_EVENTS_LIMIT = int(os.environ.get("LORE_MAX_LIST_EVENTS_LIMIT", "200"))

db = Database(DB_PATH)
engine = LineageEngine(db)
pack_builder = ContextPackBuilder(db)
embedding_provider = None

app = Server("lore-governed-memory")
logger = logging.getLogger(__name__)
_DEFAULT_SALT_WARNING_EMITTED = False
_token_verifier: OIDCTokenVerifier | None = None
_token_verifier_error: Exception | None = None
_token_verifier_lock = threading.Lock()
_federation_worker: FederationWorker | None = None
READ_ONLY_SAFE_TOOLS = {
    "retrieve_context_pack",
    "audit_trace",
    "list_events",
    "export_domain",
    "export_subject_data",
    "generate_processing_record",
    "audit_anomaly_scan",
    "verify_snapshot",
}


def _get_token_verifier() -> OIDCTokenVerifier:
    global _token_verifier, _token_verifier_error
    with _token_verifier_lock:
        if _token_verifier is not None:
            return _token_verifier
        if _token_verifier_error is not None:
            raise _token_verifier_error
        try:
            _token_verifier = build_token_verifier_from_env()
        except Exception as exc:
            _token_verifier_error = exc
            raise
        return _token_verifier


def _get_embedding_provider():
    global embedding_provider
    if embedding_provider is None:
        embedding_provider = build_embedding_provider_from_env()
    return embedding_provider


def _reset_runtime_state_for_tests() -> None:
    global _token_verifier, _token_verifier_error
    global embedding_provider, _DEFAULT_SALT_WARNING_EMITTED
    global _federation_worker
    with _token_verifier_lock:
        _token_verifier = None
        _token_verifier_error = None
        embedding_provider = None
        _DEFAULT_SALT_WARNING_EMITTED = False
        _federation_worker = None
    reset_context_pack_runtime_state_for_tests()
    reset_metrics_for_tests()


def _get_federation_worker() -> FederationWorker:
    global _federation_worker
    if _federation_worker is None:
        node_id = os.environ.get("LORE_FEDERATION_NODE_ID", "").strip() or "node-local"
        _federation_worker = FederationWorker(db=db, node_id=node_id)
    return _federation_worker


def _get_compliance_service() -> ComplianceService:
    return ComplianceService(db=db, engine=engine)


def _get_consent_service() -> ConsentService:
    return ConsentService(db=db)


def _get_dr_service() -> DRService:
    snapshot_dir = os.environ.get("LORE_DR_SNAPSHOT_DIR", "lore_snapshots")
    return DRService(db=db, db_path=DB_PATH, snapshot_dir=snapshot_dir)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="store_event",
            description=(
                "Store important personal facts the user shares (health, career, finance, "
                "relationships, preferences, decisions). Use this when the user reveals new "
                "personal context that should be durable and auditable. "
                "Example: store_event(domains=['health'], "
                "type='med_started', payload={'name':'metformin'})."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["general"],
                    },
                    "content": {"type": "string", "default": ""},
                    "type": {"type": "string", "default": "note"},
                    "payload": {"type": "object", "default": {}},
                    "sensitivity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "restricted"],
                        "default": "high",
                    },
                    "consent_source": {"type": "string", "default": "implicit"},
                    "expires_at": {"type": "string"},
                    "metadata": {"type": "object", "default": {}},
                    "source": {"type": "string", "default": "user"},
                    "ts": {"type": "string"},
                },
                "required": ["domains"],
            },
        ),
        Tool(
            name="retrieve_context_pack",
            description=(
                "Retrieve bounded personal context for a domain before using its own memory. "
                "Returns facts, summary, and retrieval metadata filtered by sensitivity. "
                "Example: retrieve_context_pack(domain='health', query='what meds am I on?')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "default": "general"},
                    "query": {"type": "string", "default": ""},
                    "include_summary": {"type": "boolean", "default": True},
                    "max_sensitivity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "default": "high",
                    },
                    "limit": {"type": "integer", "default": 50},
                    "agent_id": {"type": "string", "default": ""},
                    "session_id": {"type": "string", "default": ""},
                },
            },
        ),
        Tool(
            name="delete_and_recompute",
            description=(
                "Delete an event or fact and recompute downstream lineage. "
                "Use mode='soft' for reversible governance deletion and mode='hard' for "
                "physical erasure/audit compliance. "
                "Example: delete_and_recompute(target_id='event:...', "
                "target_type='event', mode='hard')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "target_type": {"type": "string", "enum": ["event", "fact"]},
                    "reason": {"type": "string", "default": ""},
                    "mode": {"type": "string", "enum": ["soft", "hard"], "default": "soft"},
                    "run_vacuum": {"type": "boolean", "default": False},
                },
                "required": ["target_id", "target_type"],
            },
        ),
        Tool(
            name="audit_trace",
            description=(
                "Get full lineage trace for an event or fact. Use include_source_events=true "
                "for drill-down into raw contributing events."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "include_source_events": {"type": "boolean", "default": False},
                },
                "required": ["item_id"],
            },
        ),
        Tool(
            name="list_events",
            description=(
                "List events with domain filtering and pagination for full-history review. "
                "Use include_tombstoned=true for compliance/audit views."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "default": "general"},
                    "limit": {"type": "integer", "default": 50},
                    "offset": {"type": "integer", "default": 0},
                    "include_tombstoned": {"type": "boolean", "default": False},
                },
            },
        ),
        Tool(
            name="export_domain",
            description=(
                "Export complete domain data for right-to-access workflows. Returns events, facts, "
                "and lineage edges in json, markdown, or timeline format."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "default": "general"},
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown", "timeline"],
                        "default": "json",
                    },
                    "confirm_restricted": {"type": "boolean", "default": False},
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="erase_subject_data",
            description=(
                "Erase all active subject-linked records and cascade recompute with deletion proof."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "subject_id": {"type": "string"},
                    "mode": {"type": "string", "enum": ["soft", "hard"], "default": "hard"},
                    "reason": {"type": "string", "default": "subject_erasure"},
                },
                "required": ["subject_id"],
            },
        ),
        Tool(
            name="export_subject_data",
            description=(
                "Export all active subject-linked records with deterministic integrity manifest."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "subject_id": {"type": "string"},
                },
                "required": ["subject_id"],
            },
        ),
        Tool(
            name="record_consent",
            description="Record consent status changes for a subject and processing purpose.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject_id": {"type": "string"},
                    "purpose": {"type": "string", "default": "retrieval"},
                    "status": {"type": "string"},
                    "legal_basis": {"type": "string", "default": ""},
                    "source": {"type": "string", "default": "user"},
                    "metadata": {"type": "object", "default": {}},
                },
                "required": ["subject_id", "status"],
            },
        ),
        Tool(
            name="generate_processing_record",
            description="Generate Article 30-style data processing record for the tenant.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="audit_anomaly_scan",
            description="Scan audit events for suspicious access patterns over a recent window.",
            inputSchema={
                "type": "object",
                "properties": {
                    "window_minutes": {"type": "integer", "default": 60},
                    "limit": {"type": "integer", "default": 500},
                },
            },
        ),
        Tool(
            name="create_snapshot",
            description="Create a DR snapshot of the current tenant database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "label": {"type": "string", "default": "manual"},
                },
            },
        ),
        Tool(
            name="verify_snapshot",
            description="Verify snapshot integrity checksum.",
            inputSchema={
                "type": "object",
                "properties": {
                    "snapshot_id": {"type": "string"},
                },
                "required": ["snapshot_id"],
            },
        ),
        Tool(
            name="restore_snapshot",
            description="Restore a previously captured DR snapshot.",
            inputSchema={
                "type": "object",
                "properties": {
                    "snapshot_id": {"type": "string"},
                },
                "required": ["snapshot_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    request_id = ""
    tenant_token = None
    try:
        args = dict(arguments or {})
        request_id = _resolve_request_id(args)
        args["_request_id"] = request_id
        token = extract_auth_token(args)
        try:
            access = await _get_token_verifier().verify_token(token)
        except Exception as exc:
            logger.error("server_misconfigured tool=%s error=%s", name, exc)
            raise PermissionError("server_misconfigured") from exc
        if access is None:
            audit.log_security_event(
                name,
                "deny",
                request_id=request_id,
                details={"reason": "unauthorized"},
            )
            raise PermissionError("unauthorized")
        try:
            authorize_action(set(access.scopes), name)
        except PermissionError as exc:
            audit.log_security_event(
                name,
                "deny",
                principal_id=access.client_id,
                request_id=request_id,
                details={"reason": "forbidden", "error": str(exc)},
            )
            raise PermissionError(f"forbidden:{exc}") from exc

        args["_auth_scopes"] = list(access.scopes)
        args["_auth_client_id"] = access.client_id
        tenant_context = resolve_tenant_context(
            claims={"sub": access.client_id, "tenant_id": access.resource or ""},
            args=args,
        )
        args["_auth_tenant_id"] = tenant_context.tenant_id
        tenant_token = set_current_tenant_context(tenant_context)
        if agent_permissions_enabled():
            policy = PolicyEngine(db, shadow_mode=policy_shadow_mode_enabled())
            principal_agent = access.client_id
            if name == "retrieve_context_pack":
                domain = str(args.get("domain", "general") or "general")
                if not policy.enforce_read_domain(
                    tenant_context.tenant_id, principal_agent, domain
                ):
                    raise PermissionError("forbidden:policy_denied")
            elif name in {
                "list_events",
                "export_domain",
                "audit_trace",
                "export_subject_data",
                "generate_processing_record",
                "audit_anomaly_scan",
                "verify_snapshot",
            }:
                domain = str(args.get("domain", "general") or "general")
                if not policy.enforce_read_domain(
                    tenant_context.tenant_id, principal_agent, domain
                ):
                    raise PermissionError("forbidden:policy_denied")
            elif name in {"store_event", "record_consent", "create_snapshot", "restore_snapshot"}:
                domains = args.get("domains", ["general"]) or ["general"]
                for domain in domains:
                    if not policy.enforce_write_domain(
                        tenant_context.tenant_id,
                        principal_agent,
                        str(domain or "general"),
                    ):
                        raise PermissionError("forbidden:policy_denied")
            elif name in {"delete_and_recompute", "erase_subject_data"}:
                target_id = str(args.get("target_id", ""))
                target_type = str(args.get("target_type", "event"))
                delete_domains: set[str] = set()
                if name == "erase_subject_data":
                    subject_id = str(args.get("subject_id", "")).strip()
                    delete_domains = db.get_active_domains_by_subject(
                        subject_id=subject_id,
                        tenant_id=tenant_context.tenant_id,
                    )
                elif target_type == "event":
                    target_event = db.get_event(target_id, tenant_id=tenant_context.tenant_id)
                    if target_event:
                        delete_domains.update(target_event.get("domains") or [])
                elif target_type == "fact":
                    parent_edges = db.get_parents(target_id, tenant_id=tenant_context.tenant_id)
                    for edge in parent_edges:
                        if edge.get("parent_type") != "event":
                            continue
                        parent_event = db.get_event(
                            str(edge.get("parent_id", "")),
                            tenant_id=tenant_context.tenant_id,
                        )
                        if parent_event:
                            delete_domains.update(parent_event.get("domains") or [])
                if not delete_domains:
                    delete_domains = {"general"}
                for domain in sorted(delete_domains):
                    if not policy.enforce_write_domain(
                        tenant_context.tenant_id,
                        principal_agent,
                        str(domain or "general"),
                    ):
                        raise PermissionError("forbidden:policy_denied")
        audit.log_security_event(
            name,
            "allow",
            principal_id=access.client_id,
            request_id=request_id,
        )
        if read_only_mode_enabled() and name not in READ_ONLY_SAFE_TOOLS:
            raise RuntimeError("LORE_READ_ONLY_MODE enabled")
        if name == "store_event":
            return await handle_store_event(args)
        if name == "retrieve_context_pack":
            return await handle_retrieve_context_pack(args)
        if name == "delete_and_recompute":
            return await handle_delete_and_recompute(args)
        if name == "audit_trace":
            return await handle_audit_trace(args)
        if name == "list_events":
            return await handle_list_events(args)
        if name == "export_domain":
            return await handle_export_domain(args)
        if name == "erase_subject_data":
            return await handle_erase_subject_data(args)
        if name == "export_subject_data":
            return await handle_export_subject_data(args)
        if name == "record_consent":
            return await handle_record_consent(args)
        if name == "generate_processing_record":
            return await handle_generate_processing_record(args)
        if name == "audit_anomaly_scan":
            return await handle_audit_anomaly_scan(args)
        if name == "create_snapshot":
            return await handle_create_snapshot(args)
        if name == "verify_snapshot":
            return await handle_verify_snapshot(args)
        if name == "restore_snapshot":
            return await handle_restore_snapshot(args)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except PermissionError:
        # Let MCP transport map authorization failures to protocol-level errors.
        raise
    except Exception as e:
        logger.exception("tool_handler_error tool=%s request_id=%s", name, request_id)
        raw_error = str(e)
        safe_error = (
            raw_error
            if (isinstance(e, RuntimeError) and "LORE_" in raw_error)
            else "internal_error; see server logs"
        )
        error_payload: dict[str, Any] = {
            "ok": False,
            "error": {"type": type(e).__name__, "message": safe_error},
        }
        if name == "store_event":
            error_payload["stored"] = False
        if request_id:
            error_payload["request_id"] = request_id
        return [TextContent(type="text", text=json.dumps(error_payload, indent=2))]
    finally:
        if tenant_token is not None:
            reset_current_tenant_context(tenant_token)


async def handle_store_event(args: dict) -> list[TextContent]:
    started = time.perf_counter()
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
                    text=json.dumps(
                        {
                            "stored": False,
                            "reason": reject_reason,
                        },
                        indent=2,
                    ),
                )
            ]
    elif contains_sensitive_identifier(content_basis):
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "stored": False,
                        "reason": "sensitive_credential_or_identifier",
                    },
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
    enable_semantic_dedup = os.environ.get("LORE_ENABLE_SEMANTIC_DEDUP", "0") == "1"
    if enable_semantic_dedup:
        provider = _get_embedding_provider()
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
    sensitivity = args.get("sensitivity", "high")
    plain_payload = payload
    encryption_material = _runtime_encryption_material()
    should_encrypt_payload = (
        sensitivity in {"high", "restricted"} and encryption_material is not None
    )
    event_payload = plain_payload
    if should_encrypt_payload:
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
        provider = _get_embedding_provider()
        event_embedding = provider.embed_text(content_basis)
        db.upsert_event_embedding(
            event.id,
            event_embedding,
            provider.provider_id,
            tenant_id=tenant_id or "default",
        )
    except Exception as exc:
        logger.warning("event_embedding_index_failed event_id=%s error=%s", event.id, exc)
    # Avoid deriving plaintext-bearing facts from sensitive encrypted events.
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
    limit = _clamp_positive_int(args.get("limit", 50), default=50, maximum=MAX_CONTEXT_PACK_LIMIT)
    pack = pack_builder.build(
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
    return [TextContent(type="text", text=render_prometheus())]


async def handle_health(args: dict) -> list[TextContent]:
    db_ok = db.ping()
    payload = {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "transport": get_transport_mode(),
    }
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def handle_audit_trace(args: dict) -> list[TextContent]:
    trace = engine.get_audit_trace(
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
    request_id = str(args.get("_request_id", ""))
    principal_id = str(args.get("_auth_client_id", ""))
    target_id = args["target_id"]
    target_type = args["target_type"]
    mode = args.get("mode", "soft")
    audit_result = "error"
    audit_details = {
        "target_id": target_id,
        "target_type": target_type,
        "mode": mode,
    }
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
    domain = args.get("domain", "general")
    include_tombstoned = args.get("include_tombstoned", False)
    offset = _clamp_non_negative_int(args.get("offset", 0), default=0)
    limit = _clamp_positive_int(args.get("limit", 50), default=50, maximum=MAX_LIST_EVENTS_LIMIT)
    domain_filter = [] if domain == "general" else [domain]
    total_count = db.count_events_by_domains(
        domain_filter,
        include_tombstoned=include_tombstoned,
        tenant_id=args.get("_auth_tenant_id", ""),
    )
    window = db.list_events_page(
        domains=domain_filter,
        include_tombstoned=include_tombstoned,
        limit=limit,
        offset=offset,
        tenant_id=args.get("_auth_tenant_id", ""),
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
                {
                    "total_count": total_count,
                    "count": len(window),
                    "events": window,
                },
                indent=2,
            ),
        )
    ]


async def handle_export_domain(args: dict) -> list[TextContent]:
    domain = args.get("domain", "general")
    fmt = args.get("format", "json")
    page_size = _clamp_non_negative_int(args.get("page_size", 0), default=0)
    stream_mode = bool(args.get("stream", False))
    include_hashes = bool(args.get("include_hashes", False))
    cursor = str(args.get("cursor", "")).strip()
    tenant_id = args.get("_auth_tenant_id", "")
    events = (
        db.get_active_events_by_domains([domain], tenant_id=tenant_id)
        if domain != "general"
        else db.get_active_events(tenant_id=tenant_id)
    )
    facts = db.get_current_facts_by_domain(domain, tenant_id=tenant_id)
    fact_ids = [fact["id"] for fact in facts]
    parents_by_fact = db.get_parents_for_children(fact_ids, tenant_id=tenant_id)
    parent_event_ids = sorted(
        {
            parent["parent_id"]
            for parents in parents_by_fact.values()
            for parent in parents
            if parent.get("parent_type") == "event"
        }
    )
    parent_events = db.get_events_by_ids(parent_event_ids, tenant_id=tenant_id)
    restricted = []
    for fact in facts:
        parents = parents_by_fact.get(fact["id"], [])
        for parent in parents:
            if parent["parent_type"] != "event":
                continue
            event = parent_events.get(parent["parent_id"])
            if event and event.get("sensitivity") == "restricted":
                restricted.append(fact["id"])
                break

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

    event_ids = {ev["id"] for ev in events}
    edges = []
    for fact in facts:
        for parent in parents_by_fact.get(fact["id"], []):
            if parent.get("parent_type") != "event":
                continue
            if domain != "general" and parent.get("parent_id") not in event_ids:
                continue
            edges.append(
                {
                    "from": parent["parent_id"],
                    "to": fact["id"],
                    "relation": parent["relation"],
                }
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
            cursor_key = _decode_cursor(cursor)
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


async def handle_erase_subject_data(args: dict) -> list[TextContent]:
    service = _get_compliance_service()
    result = service.erase_subject_data(
        subject_id=str(args.get("subject_id", "")),
        mode=str(args.get("mode", "hard")),
        tenant_id=str(args.get("_auth_tenant_id", "")),
        reason=str(args.get("reason", "subject_erasure")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_export_subject_data(args: dict) -> list[TextContent]:
    service = _get_compliance_service()
    result = service.export_subject_data(
        subject_id=str(args.get("subject_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_record_consent(args: dict) -> list[TextContent]:
    service = _get_consent_service()
    record_id = service.record(
        tenant_id=str(args.get("_auth_tenant_id", "default")),
        subject_id=str(args.get("subject_id", "")),
        purpose=str(args.get("purpose", "retrieval")),
        status=str(args.get("status", "")),
        legal_basis=str(args.get("legal_basis", "")),
        source=str(args.get("source", "user")),
        metadata=dict(args.get("metadata", {}) or {}),
    )
    payload = {"ok": True, "record_id": record_id}
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def handle_generate_processing_record(args: dict) -> list[TextContent]:
    report = generate_article30_report(
        db=db,
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(report, indent=2))]


async def handle_audit_anomaly_scan(args: dict) -> list[TextContent]:
    limit = _clamp_positive_int(args.get("limit", 500), default=500, maximum=5000)
    window_minutes = _clamp_positive_int(args.get("window_minutes", 60), default=60, maximum=10080)
    events = audit.get_events(limit=limit)
    alerts = scan_access_anomalies(events, window_minutes=window_minutes)
    payload = {
        "ok": True,
        "window_minutes": window_minutes,
        "events_scanned": len(events),
        "alerts": alerts,
    }
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def handle_create_snapshot(args: dict) -> list[TextContent]:
    service = _get_dr_service()
    result = service.create_snapshot(
        label=str(args.get("label", "manual")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_verify_snapshot(args: dict) -> list[TextContent]:
    service = _get_dr_service()
    result = service.verify_snapshot(
        snapshot_id=str(args.get("snapshot_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_restore_snapshot(args: dict) -> list[TextContent]:
    service = _get_dr_service()
    result = service.restore_snapshot(
        snapshot_id=str(args.get("snapshot_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    if result.get("ok"):
        result["warning"] = "restart_server_recommended_after_restore"
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def run_ttl_sweep(delete_mode: str = "soft") -> dict[str, Any]:
    now = now_iso()
    expired = db.get_expired_events(now)
    processed: list[str] = []
    for event in expired:
        engine.delete_and_recompute(event["id"], "event", reason="ttl_expired", mode=delete_mode)
        processed.append(event["id"])
    logger.info(
        "ttl_sweep mode=%s scanned=%s deleted=%s",
        delete_mode,
        len(expired),
        len(processed),
    )
    return {"checked_at": now, "count": len(processed), "event_ids": processed, "mode": delete_mode}


async def _ttl_sweep_loop(
    interval_seconds: int, delete_mode: str, stop_event: asyncio.Event
) -> None:
    while not stop_event.is_set():
        run_ttl_sweep(delete_mode=delete_mode)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(1, int(interval_seconds)))
        except TimeoutError:
            continue


def get_transport_mode() -> str:
    return os.environ.get("LORE_TRANSPORT", "streamable-http").strip().lower()


def validate_transport_mode(mode: str) -> None:
    if mode not in {"stdio", "streamable-http"}:
        raise ValueError(f"unsupported_transport:{mode}")
    if mode == "stdio" and os.environ.get("LORE_ALLOW_STDIO_DEV", "0") != "1":
        raise PermissionError("stdio transport is dev-only; set LORE_ALLOW_STDIO_DEV=1")


def _decode_tool_output(tool_output: list[TextContent]) -> Any:
    if not tool_output:
        return {}
    text = tool_output[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def _invoke_tool(name: str, arguments: dict[str, Any]) -> Any:
    return _decode_tool_output(await call_tool(name, arguments))


def build_fastmcp_server() -> FastMCP:
    server = FastMCP("lore-governed-memory")

    @server.tool(name="store_event", description="Store a memory event.")
    async def _store_event(
        domains: list[str] | None = None,
        content: str = "",
        type: str = "note",
        payload: dict[str, Any] | None = None,
        sensitivity: str = "high",
        consent_source: str = "implicit",
        expires_at: str = "",
        metadata: dict[str, Any] | None = None,
        source: str = "user",
        ts: str = "",
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "domains": domains or ["general"],
            "content": content,
            "type": type,
            "payload": payload or {},
            "sensitivity": sensitivity,
            "consent_source": consent_source,
            "metadata": metadata or {},
            "source": source,
        }
        if expires_at:
            args["expires_at"] = expires_at
        if ts:
            args["ts"] = ts
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("store_event", args)

    @server.tool(name="retrieve_context_pack", description="Retrieve memory context.")
    async def _retrieve_context_pack(
        domain: str = "general",
        query: str = "",
        include_summary: bool = True,
        max_sensitivity: str = "high",
        limit: int = 50,
        agent_id: str = "",
        session_id: str = "",
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "domain": domain,
            "query": query,
            "include_summary": include_summary,
            "max_sensitivity": max_sensitivity,
            "limit": limit,
            "agent_id": agent_id,
            "session_id": session_id,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("retrieve_context_pack", args)

    @server.tool(name="delete_and_recompute", description="Delete memory and recompute lineage.")
    async def _delete_and_recompute(
        target_id: str,
        target_type: str,
        reason: str = "",
        mode: str = "soft",
        run_vacuum: bool = False,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "target_id": target_id,
            "target_type": target_type,
            "reason": reason,
            "mode": mode,
            "run_vacuum": run_vacuum,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("delete_and_recompute", args)

    @server.tool(name="audit_trace", description="Get lineage trace for an item.")
    async def _audit_trace(
        item_id: str,
        include_source_events: bool = False,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "item_id": item_id,
            "include_source_events": include_source_events,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("audit_trace", args)

    @server.tool(name="list_events", description="List events with pagination.")
    async def _list_events(
        domain: str = "general",
        limit: int = 50,
        offset: int = 0,
        include_tombstoned: bool = False,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "domain": domain,
            "limit": limit,
            "offset": offset,
            "include_tombstoned": include_tombstoned,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("list_events", args)

    @server.tool(name="export_domain", description="Export domain events, facts, and lineage.")
    async def _export_domain(
        domain: str,
        format: str = "json",
        confirm_restricted: bool = False,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "domain": domain,
            "format": format,
            "confirm_restricted": confirm_restricted,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("export_domain", args)

    @server.tool(name="erase_subject_data", description="Erase all data for a subject.")
    async def _erase_subject_data(
        subject_id: str,
        mode: str = "hard",
        reason: str = "subject_erasure",
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "subject_id": subject_id,
            "mode": mode,
            "reason": reason,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("erase_subject_data", args)

    @server.tool(name="export_subject_data", description="Export all data for a subject.")
    async def _export_subject_data(
        subject_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"subject_id": subject_id}
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("export_subject_data", args)

    @server.tool(name="record_consent", description="Record consent status for a subject.")
    async def _record_consent(
        subject_id: str,
        status: str,
        purpose: str = "retrieval",
        legal_basis: str = "",
        source: str = "user",
        metadata: dict[str, Any] | None = None,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "subject_id": subject_id,
            "status": status,
            "purpose": purpose,
            "legal_basis": legal_basis,
            "source": source,
            "metadata": metadata or {},
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("record_consent", args)

    @server.tool(
        name="generate_processing_record",
        description="Generate Article 30 processing record for compliance.",
    )
    async def _generate_processing_record(
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {}
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("generate_processing_record", args)

    @server.tool(name="audit_anomaly_scan", description="Scan audit logs for anomaly patterns.")
    async def _audit_anomaly_scan(
        window_minutes: int = 60,
        limit: int = 500,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "window_minutes": window_minutes,
            "limit": limit,
        }
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("audit_anomaly_scan", args)

    @server.tool(name="create_snapshot", description="Create a disaster recovery snapshot.")
    async def _create_snapshot(
        label: str = "manual",
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"label": label}
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("create_snapshot", args)

    @server.tool(name="verify_snapshot", description="Verify snapshot integrity.")
    async def _verify_snapshot(
        snapshot_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"snapshot_id": snapshot_id}
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("verify_snapshot", args)

    @server.tool(name="restore_snapshot", description="Restore a snapshot into active DB.")
    async def _restore_snapshot(
        snapshot_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"snapshot_id": snapshot_id}
        if auth_token:
            args["_auth_token"] = auth_token
        if request_id:
            args["_request_id"] = request_id
        return await _invoke_tool("restore_snapshot", args)

    return server


async def run_stdio_server() -> None:
    ttl_delete_mode = os.environ.get("LORE_TTL_DELETE_MODE", "soft")
    ttl_interval_seconds = int(os.environ.get("LORE_TTL_SWEEP_INTERVAL_SECONDS", "3600"))
    run_ttl_sweep(delete_mode=ttl_delete_mode)
    stop_event = asyncio.Event()
    ttl_task = asyncio.create_task(
        _ttl_sweep_loop(ttl_interval_seconds, ttl_delete_mode, stop_event)
    )
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(read_stream, write_stream, app.create_initialization_options())
        finally:
            stop_event.set()
            ttl_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ttl_task


def main():
    try:
        _get_token_verifier()
    except Exception as exc:
        logger.error("server_misconfigured error=%s", exc)
        raise SystemExit(1) from exc
    mode = get_transport_mode()
    validate_transport_mode(mode)
    if mode == "stdio":
        asyncio.run(run_stdio_server())
        return
    build_fastmcp_server().run(transport="streamable-http")


if __name__ == "__main__":
    main()
