import asyncio

from lore.server import list_tools


def test_server_exposes_required_tools():
    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert {
        "store_event",
        "retrieve_context_pack",
        "delete_and_recompute",
        "audit_trace",
        "list_events",
        "export_domain",
        "erase_subject_data",
        "export_subject_data",
        "record_consent",
        "generate_processing_record",
        "audit_anomaly_scan",
        "create_snapshot",
        "verify_snapshot",
        "restore_snapshot",
    } <= names
