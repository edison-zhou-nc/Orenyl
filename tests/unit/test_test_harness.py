from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_conftest_does_not_seed_oidc_issuer_globally() -> None:
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text()

    assert "LORE_OIDC_ISSUER" not in conftest
