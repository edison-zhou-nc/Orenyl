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
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import audit, env_vars
from . import context_pack as context_pack_module
from .auth import (
    OIDCTokenVerifier,
    all_authorization_scopes,
    authorize_action,
    build_token_verifier_from_env,
    extract_auth_token,
)
from .compliance import ComplianceService
from .config import auth_required_for_runtime, multi_tenant_enabled, read_only_mode_enabled
from .consent import ConsentService
from .context_pack import ContextPackBuilder
from .db import Database
from .disaster_recovery import DRService
from .embedding_provider import build_embedding_provider_from_env
from .federation_worker import FederationWorker
from .handlers import compliance as compliance_handlers
from .handlers import core as core_handlers
from .handlers import operations as operations_handlers
from .handlers._common import _resolve_request_id
from .handlers.tooling import list_registered_tools, register_fastmcp_tools
from .lazy import Lazy
from .lineage import LineageEngine
from .metrics import reset_metrics_for_tests
from .models import now_iso
from .policy import (
    PolicyEngine,
    agent_permissions_enabled,
    policy_shadow_mode_enabled,
    validate_policy_configuration,
)
from .rate_limit import RateLimiter
from .tenant import (
    reset_current_tenant_context,
    resolve_tenant_context,
    set_current_tenant_context,
)

DB_PATH = os.environ.get(env_vars.DB_PATH, "lore_memory.db")
MAX_CONTEXT_PACK_LIMIT = int(os.environ.get(env_vars.MAX_CONTEXT_PACK_LIMIT, "100"))
MAX_LIST_EVENTS_LIMIT = int(os.environ.get(env_vars.MAX_LIST_EVENTS_LIMIT, "200"))

db = Database(DB_PATH)
engine = LineageEngine(db)
pack_builder = ContextPackBuilder(db)
_embedding_provider_lazy = Lazy(build_embedding_provider_from_env)

app = Server("lore-governed-memory")
logger = logging.getLogger(__name__)
_DEFAULT_SALT_WARNING_EMITTED = False
_token_verifier: OIDCTokenVerifier | None = None
_token_verifier_error: Exception | None = None
_token_verifier_lock = threading.Lock()
_federation_worker: FederationWorker | None = None
_rate_limiter = RateLimiter()
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
# Diagnostic helpers stay import-compatible on lore.server but are not MCP tools.
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
        except (RuntimeError, ValueError) as exc:
            _token_verifier_error = exc
            raise
        return _token_verifier


def _get_embedding_provider():
    return _embedding_provider_lazy.value


def _warn_on_risky_policy_configuration() -> None:
    if (
        agent_permissions_enabled()
        and policy_shadow_mode_enabled()
        and not multi_tenant_enabled()
    ):
        logger.warning(
            "policy_shadow_mode_active agent_permissions_enabled=true multi_tenant_enabled=false"
        )


def _misconfig_error_markers() -> tuple[str, ...]:
    return env_vars.all_names() + env_vars.all_prefixes()


def _rebind_runtime_state_for_tests(db_path: str | None = None) -> None:
    global DB_PATH, MAX_CONTEXT_PACK_LIMIT, MAX_LIST_EVENTS_LIMIT
    global db, engine, pack_builder, _federation_worker
    old_db = db
    DB_PATH = db_path or os.environ.get(env_vars.DB_PATH, "lore_memory.db")
    MAX_CONTEXT_PACK_LIMIT = int(os.environ.get(env_vars.MAX_CONTEXT_PACK_LIMIT, "100"))
    MAX_LIST_EVENTS_LIMIT = int(os.environ.get(env_vars.MAX_LIST_EVENTS_LIMIT, "200"))
    db = Database(DB_PATH)
    engine = LineageEngine(db)
    pack_builder = ContextPackBuilder(db)
    _federation_worker = None
    with contextlib.suppress(Exception):
        old_db.close()


def _reset_runtime_state_for_tests() -> None:
    global _token_verifier, _token_verifier_error
    global _DEFAULT_SALT_WARNING_EMITTED, _federation_worker, _rate_limiter
    with _token_verifier_lock:
        _token_verifier = None
        _token_verifier_error = None
        _embedding_provider_lazy.reset()
        _DEFAULT_SALT_WARNING_EMITTED = False
        _federation_worker = None
        _rate_limiter = RateLimiter()
    context_pack_module._reset_runtime_state_for_tests()
    reset_metrics_for_tests()


def _get_federation_worker() -> FederationWorker:
    global _federation_worker
    if _federation_worker is None:
        node_id = os.environ.get(env_vars.FEDERATION_NODE_ID, "").strip() or "node-local"
        _federation_worker = FederationWorker(db=db, node_id=node_id)
    return _federation_worker


def _get_compliance_service() -> ComplianceService:
    return ComplianceService(db=db, engine=engine)


def _get_consent_service() -> ConsentService:
    return ConsentService(db=db)


def _get_dr_service() -> DRService:
    snapshot_dir = os.environ.get(env_vars.DR_SNAPSHOT_DIR, "lore_snapshots")
    return DRService(db=db, db_path=DB_PATH, snapshot_dir=snapshot_dir)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return list_registered_tools()


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    request_id = ""
    tenant_token = None
    try:
        args = dict(arguments or {})
        request_id = _resolve_request_id(args)
        args["_request_id"] = request_id
        auth_details: dict[str, Any] = {}
        if auth_required_for_runtime():
            token = extract_auth_token(args)
            try:
                access = await _get_token_verifier().verify_token(token)
            except (RuntimeError, ValueError) as exc:
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
        else:
            access = AccessToken(
                token="",
                client_id="local-dev",
                scopes=all_authorization_scopes(),
                resource=None,
            )
            auth_details["auth_mode"] = "dev-stdio"
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
        if _rate_limiter.enabled and not _rate_limiter.allow(tenant_context.tenant_id):
            raise PermissionError("rate_limited")
        tenant_token = set_current_tenant_context(tenant_context)
        if agent_permissions_enabled():
            try:
                validate_policy_configuration()
            except RuntimeError as exc:
                logger.error("server_misconfigured tool=%s error=%s", name, exc)
                raise PermissionError("server_misconfigured") from exc
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
            details=auth_details,
        )
        if read_only_mode_enabled() and name not in READ_ONLY_SAFE_TOOLS:
            raise RuntimeError(f"{env_vars.READ_ONLY_MODE} enabled")
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
            # Preserve explicit config/runtime misconfiguration messages while
            # continuing to redact internal operational errors.
            raw_error
            if (
                isinstance(e, RuntimeError)
                and any(marker in raw_error for marker in _misconfig_error_markers())
            )
            else "internal_error; see server logs"
        )
        error_payload: dict[str, Any] = {
            "ok": False,
            "error": {"type": "internal_error", "message": safe_error},
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
    get_expired_events_global = getattr(db, "get_expired_events_global", None)
    if callable(get_expired_events_global):
        expired = get_expired_events_global(now)
    else:
        expired = db.get_expired_events(now)
    processed: list[str] = []
    for event in expired:
        engine.delete_and_recompute(
            event["id"],
            "event",
            reason="ttl_expired",
            mode=delete_mode,
            tenant_id=str(event.get("tenant_id", "") or ""),
        )
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
    return os.environ.get(env_vars.TRANSPORT, "streamable-http").strip().lower()


def validate_transport_mode(mode: str) -> None:
    if mode not in {"stdio", "streamable-http"}:
        raise ValueError(f"unsupported_transport:{mode}")
    if mode == "stdio" and os.environ.get(env_vars.ALLOW_STDIO_DEV, "0") != "1":
        raise PermissionError(
            f"stdio transport is dev-only; set {env_vars.ALLOW_STDIO_DEV}=1"
        )


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
    register_fastmcp_tools(server, _invoke_tool)
    return server


async def run_stdio_server() -> None:
    ttl_delete_mode = os.environ.get(env_vars.TTL_DELETE_MODE, "soft")
    ttl_interval_seconds = int(os.environ.get(env_vars.TTL_SWEEP_INTERVAL_SECONDS, "3600"))
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
    mode = get_transport_mode()
    validate_transport_mode(mode)
    _warn_on_risky_policy_configuration()
    try:
        validate_policy_configuration()
    except RuntimeError as exc:
        logger.error("server_misconfigured error=%s", exc)
        raise SystemExit(1) from exc
    if auth_required_for_runtime():
        try:
            _get_token_verifier()
        except (RuntimeError, ValueError) as exc:
            logger.error("server_misconfigured error=%s", exc)
            raise SystemExit(1) from exc
    if mode == "stdio":
        asyncio.run(run_stdio_server())
        return
    build_fastmcp_server().run(transport="streamable-http")


if __name__ == "__main__":
    main()
