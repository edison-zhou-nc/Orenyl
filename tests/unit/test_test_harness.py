from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_conftest_does_not_seed_oidc_issuer_globally() -> None:
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text()

    assert "ORENYL_OIDC_ISSUER" not in conftest


def test_conftest_prepends_repo_src_to_sys_path() -> None:
    conftest = (REPO_ROOT / "tests" / "conftest.py").read_text()

    assert 'SRC_ROOT = REPO_ROOT / "src"' in conftest
    assert "while str(SRC_ROOT) in sys.path:" in conftest
    assert "sys.path.remove(str(SRC_ROOT))" in conftest
    assert "sys.path.insert(0, str(SRC_ROOT))" in conftest
