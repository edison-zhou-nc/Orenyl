from lore import server
from lore.handlers.core import handle_store_event


def test_server_re_exports_core_handlers():
    assert server.handle_store_event is handle_store_event
