import base64
from pathlib import Path

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


def test_production_http_guide_exists() -> None:
    doc = (REPO_ROOT / "docs" / "guides" / "production-http.md").read_text(encoding="utf-8")

    assert "streamable-http" in doc
    assert "oidc" in doc.lower() or "hs256" in doc.lower()
    assert "lore_transport" in doc.lower()
    assert "lore_db_path" in doc.lower()
    assert "lore_audit_db_path" in doc.lower()


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


def test_production_env_example_uses_safe_base64_salt_placeholder() -> None:
    doc = (REPO_ROOT / "docs" / "guides" / "production.env.example").read_text(encoding="utf-8")

    assert "replace-with-base64-salt" not in doc
    assert "LORE_ENCRYPTION_SALT=" in doc or "# LORE_ENCRYPTION_SALT=" in doc

    salt_line = next(
        line
        for line in doc.splitlines()
        if line.startswith("LORE_ENCRYPTION_SALT=") or line.startswith("# LORE_ENCRYPTION_SALT=")
    )
    if salt_line.startswith("#"):
        return

    salt_value = salt_line.split("=", 1)[1].strip()
    base64.b64decode(salt_value, validate=True)