from pathlib import Path

from lore.handlers.tooling import list_registered_tools

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_docs_exist_and_cover_current_surface() -> None:
    required = [
        "CHANGELOG.md",
        "docs/MIGRATION.md",
        "docs/MCP_TOOL_CONTRACTS.md",
        "docs/INTEGRATION.md",
        "docs/ADR.md",
        "docs/SCALING.md",
        "docs/DR.md",
        "docs/RELEASE_PROCESS.md",
    ]

    for path in required:
        assert (REPO_ROOT / path).exists(), f"missing {path}"


def test_mcp_tool_contract_doc_covers_registered_tools() -> None:
    doc = (REPO_ROOT / "docs" / "MCP_TOOL_CONTRACTS.md").read_text()

    assert "## Common expectations" in doc
    for tool in list_registered_tools():
        heading = f"### `{tool.name}`"
        assert heading in doc, f"missing section for {tool.name}"
        section = doc.split(heading, 1)[1].split("\n### `", 1)[0]
        assert "Schema:" in section, f"missing schema details for {tool.name}"
        assert "Auth:" in section, f"missing auth details for {tool.name}"
        assert "Side effects:" in section, f"missing side effects for {tool.name}"
        assert "Sample response:" in section, f"missing sample response for {tool.name}"


def test_mcp_tool_contract_doc_examples_match_live_handlers() -> None:
    doc = (REPO_ROOT / "docs" / "MCP_TOOL_CONTRACTS.md").read_text()

    assert '"record_id":' in doc
    assert '"alerts": []' in doc
    assert '"findings": []' not in doc


def test_mcp_tool_contract_doc_covers_export_domain_streaming_and_correct_audit_auth() -> None:
    doc = (REPO_ROOT / "docs" / "MCP_TOOL_CONTRACTS.md").read_text()

    export_section = doc.split("### `export_domain`", 1)[1].split("\n### `", 1)[0]
    assert "page_size" in export_section
    assert "cursor" in export_section
    assert "stream" in export_section
    assert "include_hashes" in export_section

    audit_section = doc.split("### `audit_anomaly_scan`", 1)[1].split("\n### `", 1)[0]
    assert "memory:read" in audit_section
    assert "memory:export" not in audit_section
