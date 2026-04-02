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