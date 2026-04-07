from pathlib import Path

import orenyl

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ga_readiness() -> None:
    assert orenyl.__version__ == "1.0.0"
    assert len((REPO_ROOT / "src" / "orenyl" / "db.py").read_text().splitlines()) < 300
    assert len((REPO_ROOT / "src" / "orenyl" / "server.py").read_text().splitlines()) < 600
    readme = (REPO_ROOT / "README.md").read_text()
    assert "Zero-config start" not in readme
    assert "works out of the box" not in readme
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
