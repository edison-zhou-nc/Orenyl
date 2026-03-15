from lore import server
from lore.handlers.compliance import handle_record_consent
from lore.handlers.operations import handle_create_snapshot


def test_server_re_exports_non_core_handlers():
    assert server.handle_record_consent is handle_record_consent
    assert server.handle_create_snapshot is handle_create_snapshot
