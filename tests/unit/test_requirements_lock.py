from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_windows_only_requirements_are_platform_guarded_in_lockfile() -> None:
    lockfile = (REPO_ROOT / "requirements.lock").read_text(encoding="utf-8")

    assert 'pywin32==311 ; sys_platform == "win32"' in lockfile
