from mcp.types import TextContent

from lore import server


def test_decode_tool_output_preserves_non_dict_json():
    output = [TextContent(type="text", text='["a", 1]')]
    assert server._decode_tool_output(output) == ["a", 1]


def test_decode_tool_output_preserves_plain_text():
    output = [TextContent(type="text", text="# markdown")]
    assert server._decode_tool_output(output) == "# markdown"
