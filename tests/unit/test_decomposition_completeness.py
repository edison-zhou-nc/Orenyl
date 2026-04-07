from pathlib import Path

from orenyl import server

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_db_file_stays_under_three_hundred_lines() -> None:
    assert len((REPO_ROOT / "src" / "orenyl" / "db.py").read_text().splitlines()) < 300


def test_server_file_stays_under_six_hundred_lines() -> None:
    assert len((REPO_ROOT / "src" / "orenyl" / "server.py").read_text().splitlines()) < 600


def test_server_exports_all_current_handlers() -> None:
    handlers = {name for name in dir(server) if name.startswith("handle_")}

    # This import-compatible surface intentionally includes 14 MCP-dispatched handlers
    # plus 2 internal-only diagnostics (metrics and health).
    assert handlers == {
        "handle_audit_anomaly_scan",
        "handle_audit_trace",
        "handle_create_snapshot",
        "handle_delete_and_recompute",
        "handle_erase_subject_data",
        "handle_export_domain",
        "handle_export_subject_data",
        "handle_generate_processing_record",
        "handle_health",
        "handle_list_events",
        "handle_metrics",
        "handle_record_consent",
        "handle_restore_snapshot",
        "handle_retrieve_context_pack",
        "handle_store_event",
        "handle_verify_snapshot",
    }
