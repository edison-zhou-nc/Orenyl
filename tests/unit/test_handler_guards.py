import ast
from pathlib import Path


def test_store_event_uses_runtime_guard_instead_of_assert() -> None:
    # core.py handles security-sensitive logic; bare assert statements are stripped by
    # Python's -O optimisation flag and must not be used as runtime guards here.
    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / "src" / "orenyl" / "handlers" / "core.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    assert not assert_nodes, (
        f"Found {len(assert_nodes)} bare assert statement(s) in core.py at line(s): "
        + ", ".join(str(n.lineno) for n in assert_nodes)
    )
