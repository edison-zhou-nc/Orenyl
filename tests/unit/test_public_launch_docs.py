from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_describes_local_dev_and_production_modes() -> None:
    readme = (REPO_ROOT / "README.md").read_text()

    assert "Local development mode" in readme
    assert "Production deployment mode" in readme
    assert "production-minded" in readme


def test_quickstart_calls_out_dev_only_stdio_and_production_http() -> None:
    doc = (REPO_ROOT / "docs" / "quickstart.md").read_text()

    assert "development only" in doc
    assert "streamable-http" in doc


def test_integration_guide_distinguishes_local_dev_from_production() -> None:
    doc = (REPO_ROOT / "docs" / "INTEGRATION.md").read_text()

    assert "Local development mode" in doc
    assert "Production deployment mode" in doc


def test_client_guides_treat_stdio_as_local_dev_mode() -> None:
    claude = (REPO_ROOT / "docs" / "guides" / "claude-code.md").read_text()
    openclaw = (REPO_ROOT / "docs" / "guides" / "openclaw.md").read_text()

    assert "development only" in claude.lower()
    assert "development only" in openclaw.lower()


def test_public_install_surfaces_use_the_unique_distribution_name() -> None:
    expectations = {
        REPO_ROOT / "README.md": [
            "# Orenyl",
            "https://github.com/edison-zhou-nc/Orenyl/actions/workflows/ci.yml",
            "docs/assets/orenyl_social_preview.png",
            "git clone https://github.com/edison-zhou-nc/Orenyl.git",
            "cd Orenyl",
            "pip install orenyl-mcp-server",
            "orenyl-server",
            '"orenyl": {',
            "orenyl_memory.db",
            "orenyl_audit.db",
            "orenyl_snapshots",
            "Code layout: `src/orenyl/`",
        ],
        REPO_ROOT / "docs" / "quickstart.md": [
            "pip install orenyl-mcp-server",
            "orenyl-server",
            '"orenyl": {',
            "ORENYL_DB_PATH\": \"./orenyl_memory.db\"",
        ],
        REPO_ROOT / "docs" / "INTEGRATION.md": ["orenyl-server", "python -m orenyl.server"],
        REPO_ROOT / "docs" / "guides" / "claude-code.md": [
            "orenyl-server",
            '"orenyl": {',
            "ORENYL_DB_PATH\": \"./orenyl_memory.db\"",
        ],
        REPO_ROOT / "docs" / "guides" / "openclaw.md": [
            "pip install orenyl-mcp-server",
            "orenyl-server",
            '"orenyl": {',
            "Orenyl",
        ],
        REPO_ROOT / "examples" / "meeting-memory" / "README.md": [
            "pip install orenyl-mcp-server",
            "Orenyl",
        ],
        REPO_ROOT / "examples" / "personal-health-tracker" / "README.md": [
            "pip install orenyl-mcp-server",
            "Orenyl",
        ],
        REPO_ROOT / "examples" / "multi-agent-shared-memory" / "README.md": [
            "pip install orenyl-mcp-server",
            "Orenyl",
        ],
    }
    forbidden_patterns = [
        r"\bpip install lore-mcp\b(?!-)",
        r"`lore-mcp` installed",
        r"lore-mcp-server",
        r"\blore-server\b",
        r"python -m lore\.server",
        r'\[\s*"-m"\s*,\s*"lore\.server"\s*\]',
    ]

    for path, expected_strings in expectations.items():
        content = path.read_text()
        for expected in expected_strings:
            assert expected in content, (
                f"missing public launch reference in {path.relative_to(REPO_ROOT)}"
            )
        for pattern in forbidden_patterns:
            assert re.search(pattern, content) is None, (
                f"stale launch name in {path.relative_to(REPO_ROOT)}"
            )
