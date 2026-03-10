import asyncio

from lore import server
from lore.models import ContextPack


class _CaptureBuilder:
    def __init__(self):
        self.last_args = None

    def build(self, **kwargs):
        self.last_args = kwargs
        return ContextPack(domain=kwargs["domain"], summary="ok")


def test_retrieve_context_pack_infers_health_domain_from_query(monkeypatch):
    capture = _CaptureBuilder()
    monkeypatch.setattr(server, "pack_builder", capture)

    asyncio.run(server.handle_retrieve_context_pack({
        "domain": "general",
        "query": "what meds am I on?",
        "limit": 5,
    }))

    assert capture.last_args is not None
    assert capture.last_args["domain"] == "health"
    assert "medications" in capture.last_args["query"]
