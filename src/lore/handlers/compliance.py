"""Compliance-focused MCP handlers extracted from server.py."""

from __future__ import annotations

import json

from mcp.types import TextContent

from ..article30 import generate_article30_report
from ._deps import get_compliance_service, get_consent_service, get_db

VALID_CONSENT_STATUSES = {"granted", "denied", "withdrawn", "pending"}


async def handle_erase_subject_data(args: dict) -> list[TextContent]:
    subject_id = str(args.get("subject_id", "")).strip()
    if not subject_id:
        return [TextContent(type="text", text=json.dumps({"error": "subject_id_required"}, indent=2))]
    service = get_compliance_service()
    result = service.erase_subject_data(
        subject_id=subject_id,
        mode=str(args.get("mode", "hard")),
        tenant_id=str(args.get("_auth_tenant_id", "")),
        reason=str(args.get("reason", "subject_erasure")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_export_subject_data(args: dict) -> list[TextContent]:
    service = get_compliance_service()
    result = service.export_subject_data(
        subject_id=str(args.get("subject_id", "")),
        tenant_id=str(args.get("_auth_tenant_id", "")),
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_record_consent(args: dict) -> list[TextContent]:
    status = str(args.get("status", "")).strip().lower()
    if status not in VALID_CONSENT_STATUSES:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "invalid_consent_status",
                        "detail": f"status must be one of: {', '.join(sorted(VALID_CONSENT_STATUSES))}",
                    },
                    indent=2,
                ),
            )
        ]
    service = get_consent_service()
    record_id = service.record(
        tenant_id=str(args.get("_auth_tenant_id", "default")),
        subject_id=str(args.get("subject_id", "")),
        purpose=str(args.get("purpose", "retrieval")),
        status=status,
        legal_basis=str(args.get("legal_basis", "")),
        source=str(args.get("source", "user")),
        metadata=dict(args.get("metadata", {}) or {}),
    )
    payload = {"ok": True, "record_id": record_id}
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def handle_generate_processing_record(args: dict) -> list[TextContent]:
    report = generate_article30_report(
        db=get_db(),
        tenant_id=str(args.get("_auth_tenant_id", "default")),
    )
    return [TextContent(type="text", text=json.dumps(report, indent=2))]
