from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_story_first_surfaces_lead_with_problem_and_proof() -> None:
    readme_lines = [
        line.strip()
        for line in (REPO_ROOT / "README.md").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    positioning = (REPO_ROOT / "docs" / "positioning.md").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    hero_hook = "Your AI agent remembers everything. Can you prove it forgot?"
    product_answer = "Orenyl is agent memory with deletion guarantees."
    proof_claim = (
        "When data is removed, every derived insight is traced, invalidated, and recomputed "
        "so deleted information does not resurface."
    )

    assert hero_hook in readme_lines[:15]
    assert product_answer in readme_lines[:15]
    assert proof_claim in readme_lines[:15]
    assert readme_lines.index(hero_hook) < readme_lines.index(product_answer) < readme_lines.index(
        proof_claim
    )
    assert readme_lines.index(hero_hook) < readme_lines.index("![Orenyl social preview](docs/assets/orenyl_social_preview.png)")
    assert "agent memory with deletion guarantees" in pyproject
    assert "## hero hook" in positioning.lower()
    assert hero_hook in positioning
    assert "## product answer" in positioning.lower()
    assert product_answer in positioning
    assert "## proof claim" in positioning.lower()
    assert proof_claim in positioning
