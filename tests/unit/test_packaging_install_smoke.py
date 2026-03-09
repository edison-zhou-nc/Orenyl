import importlib


def test_import_LORE_package():
    importlib.import_module("lore")
    importlib.import_module("lore.server")
