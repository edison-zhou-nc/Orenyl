from pathlib import Path

from orenyl import env_vars

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_configuration_mentions_all_supported_env_vars():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    missing = [name for name in env_vars.all_names() if name not in readme]
    assert missing == []


def test_readme_documents_correct_default_values():
    """Documented defaults must match runtime defaults in the source of truth."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    # Each entry is (env_var_name, expected_default_cell) â€” the literal value shown
    # in the README table's default column.  Update this list when runtime defaults change.
    expected_defaults = [
        ("LORE_RATE_LIMIT_RPM", "`100`"),
        ("LORE_COMPLIANCE_STRICT_MODE", "`1`"),
        ("LORE_VECTOR_BACKEND", "`local`"),
        ("LORE_EMBEDDING_TIMEOUT_SECONDS", "`10`"),
        ("LORE_OIDC_CLOCK_SKEW_SECONDS", "`30`"),
    ]

    wrong = []
    for name, expected in expected_defaults:
        # Match the table row: | `VAR_NAME` | `default` |
        if f"| `{name}` | {expected}" not in readme:
            wrong.append(f"{name}: expected default {expected}")
    assert wrong == [], "README default values disagree with runtime:\n" + "\n".join(wrong)
