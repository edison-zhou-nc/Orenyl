import importlib
import unittest


class ImportTests(unittest.TestCase):
    def test_run_eval_imports(self):
        importlib.import_module("run_eval")

    def test_lore_server_imports(self):
        importlib.import_module("lore.server")


if __name__ == "__main__":
    unittest.main()
