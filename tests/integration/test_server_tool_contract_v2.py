import asyncio

from lore.server import list_tools


def test_server_exposes_required_tools():
    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert names == {
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
    }


def test_export_domain_schema_exposes_pagination_and_streaming_fields():
    tools = asyncio.run(list_tools())
    export_domain = next(tool for tool in tools if tool.name == "export_domain")
    props = export_domain.inputSchema["properties"]

    assert "page_size" in props
    assert "cursor" in props
    assert "stream" in props
    assert "include_hashes" in props


def test_store_event_schema_defaults_sensitivity_to_medium():
    tools = asyncio.run(list_tools())
    store_event = next(tool for tool in tools if tool.name == "store_event")
    props = store_event.inputSchema["properties"]

    assert props["sensitivity"]["default"] == "medium"
