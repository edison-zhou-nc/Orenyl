"""Lore Governed Memory MCP Server."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import threading
from typing import Any

from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import audit
from .auth import (
    OIDCTokenVerifier,
    authorize_action,
    build_token_verifier_from_env,
    extract_auth_token,
)
from .compliance import ComplianceService
from .config import read_only_mode_enabled
from .consent import ConsentService
from .context_pack import ContextPackBuilder
from .context_pack import (
    _reset_runtime_state_for_tests as reset_context_pack_runtime_state_for_tests,
)
from .db import Database
from .disaster_recovery import DRService
from .embedding_provider import build_embedding_provider_from_env
from .federation_worker import FederationWorker
from .handlers import compliance as compliance_handlers
from .handlers import core as core_handlers
from .handlers import operations as operations_handlers
from .handlers._common import _resolve_request_id
from .lineage import LineageEngine
from .metrics import reset_metrics_for_tests
from .models import now_iso
from .policy import (
    PolicyEngine,
    agent_permissions_enabled,
    policy_shadow_mode_enabled,
)
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

handle_store_event = core_handlers.handle_store_event
handle_retrieve_context_pack = core_handlers.handle_retrieve_context_pack
handle_metrics = core_handlers.handle_metrics
handle_health = core_handlers.handle_health
handle_audit_trace = core_handlers.handle_audit_trace
handle_delete_and_recompute = core_handlers.handle_delete_and_recompute
handle_list_events = core_handlers.handle_list_events
handle_export_domain = core_handlers.handle_export_domain
handle_erase_subject_data = compliance_handlers.handle_erase_subject_data
handle_export_subject_data = compliance_handlers.handle_export_subject_data
handle_record_consent = compliance_handlers.handle_record_consent
handle_generate_processing_record = compliance_handlers.handle_generate_processing_record
handle_audit_anomaly_scan = operations_handlers.handle_audit_anomaly_scan
handle_create_snapshot = operations_handlers.handle_create_snapshot
handle_verify_snapshot = operations_handlers.handle_verify_snapshot
handle_restore_snapshot = operations_handlers.handle_restore_snapshot


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
