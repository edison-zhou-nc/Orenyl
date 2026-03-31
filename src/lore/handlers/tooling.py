"""Shared MCP tool definitions and FastMCP registration helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

InvokeTool = Callable[[str, dict[str, Any]], Awaitable[Any]]

_REGISTERED_TOOLS = (
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
                    "default": "medium",
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
                    "enum": ["low", "medium", "high", "restricted"],
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
                "page_size": {"type": "integer", "default": 0},
                "cursor": {"type": "string", "default": ""},
                "stream": {"type": "boolean", "default": False},
                "include_hashes": {"type": "boolean", "default": False},
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
        description="Create a database-wide DR snapshot in single-tenant deployments.",
        inputSchema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "manual"},
            },
        },
    ),
    Tool(
        name="verify_snapshot",
        description="Verify a database-wide snapshot checksum in single-tenant deployments.",
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
        description="Restore a database-wide snapshot in single-tenant deployments.",
        inputSchema={
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string"},
            },
            "required": ["snapshot_id"],
        },
    ),
)

_TOOL_DESCRIPTIONS = {tool.name: tool.description or "" for tool in _REGISTERED_TOOLS}


def list_registered_tools() -> list[Tool]:
    return list(_REGISTERED_TOOLS)


def _maybe_add_auth(args: dict[str, Any], auth_token: str, request_id: str) -> None:
    if auth_token:
        args["_auth_token"] = auth_token
    if request_id:
        args["_request_id"] = request_id


def register_fastmcp_tools(server: FastMCP, invoke_tool: InvokeTool) -> None:
    @server.tool(name="store_event", description=_TOOL_DESCRIPTIONS["store_event"])
    async def _store_event(
        domains: list[str] | None = None,
        content: str = "",
        type: str = "note",
        payload: dict[str, Any] | None = None,
        sensitivity: str = "medium",
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("store_event", args)

    @server.tool(
        name="retrieve_context_pack",
        description=_TOOL_DESCRIPTIONS["retrieve_context_pack"],
    )
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("retrieve_context_pack", args)

    @server.tool(
        name="delete_and_recompute",
        description=_TOOL_DESCRIPTIONS["delete_and_recompute"],
    )
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("delete_and_recompute", args)

    @server.tool(name="audit_trace", description=_TOOL_DESCRIPTIONS["audit_trace"])
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("audit_trace", args)

    @server.tool(name="list_events", description=_TOOL_DESCRIPTIONS["list_events"])
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("list_events", args)

    @server.tool(name="export_domain", description=_TOOL_DESCRIPTIONS["export_domain"])
    async def _export_domain(
        domain: str,
        format: str = "json",
        confirm_restricted: bool = False,
        page_size: int = 0,
        cursor: str = "",
        stream: bool = False,
        include_hashes: bool = False,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {
            "domain": domain,
            "format": format,
            "confirm_restricted": confirm_restricted,
            "page_size": page_size,
            "cursor": cursor,
            "stream": stream,
            "include_hashes": include_hashes,
        }
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("export_domain", args)

    @server.tool(
        name="erase_subject_data",
        description=_TOOL_DESCRIPTIONS["erase_subject_data"],
    )
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("erase_subject_data", args)

    @server.tool(
        name="export_subject_data",
        description=_TOOL_DESCRIPTIONS["export_subject_data"],
    )
    async def _export_subject_data(
        subject_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"subject_id": subject_id}
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("export_subject_data", args)

    @server.tool(
        name="record_consent",
        description=_TOOL_DESCRIPTIONS["record_consent"],
    )
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("record_consent", args)

    @server.tool(
        name="generate_processing_record",
        description=_TOOL_DESCRIPTIONS["generate_processing_record"],
    )
    async def _generate_processing_record(
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {}
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("generate_processing_record", args)

    @server.tool(
        name="audit_anomaly_scan",
        description=_TOOL_DESCRIPTIONS["audit_anomaly_scan"],
    )
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
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("audit_anomaly_scan", args)

    @server.tool(
        name="create_snapshot",
        description=_TOOL_DESCRIPTIONS["create_snapshot"],
    )
    async def _create_snapshot(
        label: str = "manual",
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"label": label}
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("create_snapshot", args)

    @server.tool(
        name="verify_snapshot",
        description=_TOOL_DESCRIPTIONS["verify_snapshot"],
    )
    async def _verify_snapshot(
        snapshot_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"snapshot_id": snapshot_id}
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("verify_snapshot", args)

    @server.tool(
        name="restore_snapshot",
        description=_TOOL_DESCRIPTIONS["restore_snapshot"],
    )
    async def _restore_snapshot(
        snapshot_id: str,
        auth_token: str = "",
        request_id: str = "",
    ) -> Any:
        args: dict[str, Any] = {"snapshot_id": snapshot_id}
        _maybe_add_auth(args, auth_token, request_id)
        return await invoke_tool("restore_snapshot", args)
