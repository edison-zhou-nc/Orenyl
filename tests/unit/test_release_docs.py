from pathlib import Path


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
        assert Path(path).exists(), f"missing {path}"
