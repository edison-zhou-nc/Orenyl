import importlib

import pytest


def test_import_ORENYL_package():
    try:
        importlib.import_module("orenyl")
        importlib.import_module("orenyl.server")
    except ImportError:
        pytest.fail(
            "expected the orenyl package and server module to be importable",
            pytrace=False,
        )