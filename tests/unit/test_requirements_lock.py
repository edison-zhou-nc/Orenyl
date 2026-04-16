from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_windows_only_requirements_are_platform_guarded_in_lockfile() -> None:
    lockfile = (REPO_ROOT / "requirements.lock").read_text(encoding="utf-8")

    assert 'pywin32==311 ; sys_platform == "win32"' in lockfile


def test_cryptography_dependency_is_pinned_to_fixed_version() -> None:
    requirements_txt = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lockfile = (REPO_ROOT / "requirements.lock").read_text(encoding="utf-8")

    assert "cryptography>=46.0.7,<47" in requirements_txt
    assert '  "cryptography>=46.0.7,<47",' in pyproject
    assert "cryptography==46.0.7 \\" in lockfile


def test_python_multipart_dependency_is_pinned_to_fixed_version() -> None:
    requirements_txt = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lockfile = (REPO_ROOT / "requirements.lock").read_text(encoding="utf-8")

    assert "python-multipart>=0.0.26" in requirements_txt
    assert '  "python-multipart>=0.0.26",' in pyproject
    assert "python-multipart==0.0.26 \\" in lockfile
