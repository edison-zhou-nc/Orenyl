import base64
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_describes_local_dev_and_production_modes() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Local development mode" in readme
    assert "Production deployment mode" in readme
    assert "production-minded" in readme


def test_quickstart_calls_out_dev_only_stdio_and_production_http() -> None:
    doc = (REPO_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")

    assert "development only" in doc
    assert "streamable-http" in doc


def test_integration_guide_distinguishes_local_dev_from_production() -> None:
    doc = (REPO_ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")

    assert "Local development mode" in doc
    assert "Production deployment mode" in doc


def test_client_guides_treat_stdio_as_local_dev_mode() -> None:
    claude = (REPO_ROOT / "docs" / "guides" / "claude-code.md").read_text(encoding="utf-8")
    openclaw = (REPO_ROOT / "docs" / "guides" / "openclaw.md").read_text(encoding="utf-8")

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
            'ORENYL_DB_PATH": "./orenyl_memory.db"',
        ],
        REPO_ROOT / "docs" / "INTEGRATION.md": ["orenyl-server", "python -m orenyl.server"],
        REPO_ROOT / "docs" / "guides" / "claude-code.md": [
            "orenyl-server",
            '"orenyl": {',
            'ORENYL_DB_PATH": "./orenyl_memory.db"',
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
    for path, expected_strings in expectations.items():
        content = path.read_text(encoding="utf-8")
        for expected in expected_strings:
            assert expected in content, (
                f"missing public launch reference in {path.relative_to(REPO_ROOT)}"
            )

    assert (REPO_ROOT / "docs" / "assets" / "orenyl_social_preview.png").exists()


def test_production_http_guide_exists() -> None:
    doc = (REPO_ROOT / "docs" / "guides" / "production-http.md").read_text(encoding="utf-8")

    assert "streamable-http" in doc
    assert "oidc" in doc.lower() or "hs256" in doc.lower()
    assert "orenyl_transport" in doc.lower()
    assert "orenyl_db_path" in doc.lower()
    assert "orenyl_audit_db_path" in doc.lower()


def test_integration_guide_uses_relative_production_links() -> None:
    doc = (REPO_ROOT / "docs" / "INTEGRATION.md").read_text(encoding="utf-8")

    assert "](guides/production-http.md)" in doc
    assert "](guides/production.env.example)" in doc
    assert "](docs/guides/production-http.md)" not in doc
    assert "](docs/guides/production.env.example)" not in doc


def test_production_http_guide_mentions_hs256_minimum_bytes() -> None:
    doc = (REPO_ROOT / "docs" / "guides" / "production-http.md").read_text(encoding="utf-8")

    assert "hs256" in doc.lower()
    assert "at least 32 bytes" in doc.lower()
    assert "replace-with-at-least-32-random-bytes" in doc
    assert "replace-with-a-secret" not in doc
    assert "powershell" in doc.lower()
    assert "same environment variables apply on linux and macos" in doc.lower()


def test_production_env_example_uses_safe_base64_salt_placeholder() -> None:
    doc = (REPO_ROOT / "docs" / "guides" / "production.env.example").read_text(encoding="utf-8")
    lines = doc.splitlines()

    assert "# ORENYL_ENCRYPTION_PASSPHRASE=replace-with-secret" in lines
    assert "replace-with-base64-salt" not in doc
    assert "ORENYL_ENCRYPTION_PASSPHRASE=replace-with-secret" not in lines
    assert all(not line.startswith("ORENYL_ENCRYPTION_SALT=") for line in lines)
    assert all(not line.startswith("ORENYL_ENCRYPTION_PASSPHRASE=replace-with-secret") for line in lines)
    salt_line = next(line for line in lines if line.startswith("# ORENYL_ENCRYPTION_SALT="))
    salt_value = salt_line.split("=", 1)[1].strip()
    assert base64.b64decode(salt_value, validate=True)
