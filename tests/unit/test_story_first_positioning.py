from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_story_first_surfaces_lead_with_problem_and_proof() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "can you prove it forgot" in readme
    assert "agent memory with deletion guarantees" in readme
    assert "agent memory with deletion guarantees" in pyproject
