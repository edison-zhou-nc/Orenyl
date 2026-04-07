import asyncio

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from orenyl import server
from orenyl.handlers.tooling import list_registered_tools, register_fastmcp_tools


def test_decode_tool_output_preserves_non_dict_json():
    output = [TextContent(type="text", text='["a", 1]')]
    assert server._decode_tool_output(output) == ["a", 1]


def test_decode_tool_output_preserves_plain_text():
    output = [TextContent(type="text", text="# markdown")]
    assert server._decode_tool_output(output) == "# markdown"


def test_fastmcp_bridge_reuses_registered_tool_descriptions():
    async def invoke_tool(name: str, args: dict[str, object]) -> dict[str, object]:
        return {"name": name, "args": args}

    async def run() -> None:
        app = FastMCP("test")
        register_fastmcp_tools(app, invoke_tool)
        registered = {tool.name: tool.description for tool in list_registered_tools()}
        bridged = {tool.name: tool.description for tool in await app.list_tools()}

        assert bridged == registered

    asyncio.run(run())


def test_fastmcp_bridge_exposes_export_domain_pagination_and_streaming_fields():
    async def invoke_tool(name: str, args: dict[str, object]) -> dict[str, object]:
        return {"name": name, "args": args}

    async def run() -> None:
        app = FastMCP("test")
        register_fastmcp_tools(app, invoke_tool)
        export_domain = next(
            tool for tool in await app.list_tools() if tool.name == "export_domain"
        )
        props = export_domain.inputSchema["properties"]

        assert "page_size" in props
        assert "cursor" in props
        assert "stream" in props
        assert "include_hashes" in props

    asyncio.run(run())


def test_fastmcp_bridge_store_event_defaults_sensitivity_to_medium():
    async def invoke_tool(name: str, args: dict[str, object]) -> dict[str, object]:
        return {"name": name, "args": args}

    async def run() -> None:
        app = FastMCP("test")
        register_fastmcp_tools(app, invoke_tool)
        store_event = next(tool for tool in await app.list_tools() if tool.name == "store_event")
        props = store_event.inputSchema["properties"]

        assert props["sensitivity"]["default"] == "medium"

    asyncio.run(run())
