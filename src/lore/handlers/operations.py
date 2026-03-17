"""Operational MCP handlers extracted from server.py."""

from __future__ import annotations

import json

from mcp.types import TextContent

from .. import audit
from ..audit_anomaly import scan_access_anomalies
from ._common import _clamp_positive_int
from ._deps import get_dr_service


async def handle_audit_anomaly_scan(args: dict) -> list[TextContent]:
    limit = _clamp_positive_int(args.get("limit", 500), default=500, maximum=5000)
    window_minutes = _clamp_positive_int(
        args.get("window_minutes", 60),
        default=60,
        maximum=10080,
    )
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
    service = get_dr_service()
    result = service.create_snapshot(
        label=str(args.get("label", "manual")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_verify_snapshot(args: dict) -> list[TextContent]:
    service = get_dr_service()
    result = service.verify_snapshot(
        snapshot_id=str(args.get("snapshot_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_restore_snapshot(args: dict) -> list[TextContent]:
    service = get_dr_service()
    result = service.restore_snapshot(
        snapshot_id=str(args.get("snapshot_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    if result.get("ok"):
        result["warning"] = "restart_server_recommended_after_restore"
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
