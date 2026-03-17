import asyncio

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from lore import server
from lore.handlers.tooling import list_registered_tools, register_fastmcp_tools


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
