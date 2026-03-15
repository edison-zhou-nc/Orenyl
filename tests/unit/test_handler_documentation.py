import inspect

from lore.handlers import _deps, core


def test_deps_module_docstring_explains_server_singleton_coupling() -> None:
    docstring = inspect.getdoc(_deps)

    assert docstring is not None
    assert "server's module-level singletons" in docstring
    assert "not designed for standalone use outside the server context" in docstring


def test_diagnostic_handlers_are_documented_as_internal_only() -> None:
    expected = "Internal-only diagnostic endpoint"

    assert expected in inspect.getdoc(core.handle_metrics)
    assert expected in inspect.getdoc(core.handle_health)
