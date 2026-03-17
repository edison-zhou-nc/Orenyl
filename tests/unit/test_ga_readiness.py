from pathlib import Path

import lore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ga_readiness() -> None:
    assert lore.__version__ == "1.0.0"
    assert len((REPO_ROOT / "src" / "lore" / "db.py").read_text().splitlines()) < 300
    assert len((REPO_ROOT / "src" / "lore" / "server.py").read_text().splitlines()) < 600
    for path in [
        "CHANGELOG.md",
        "docs/MIGRATION.md",
        "docs/MCP_TOOL_CONTRACTS.md",
        "docs/INTEGRATION.md",
        "docs/ADR.md",
        "docs/SCALING.md",
        "docs/DR.md",
        "docs/SECURITY_AUDIT.md",
        "docs/COMPLIANCE_READINESS.md",
        "docs/RELEASE_PROCESS.md",
    ]:
        assert (REPO_ROOT / path).exists(), f"missing {path}"
