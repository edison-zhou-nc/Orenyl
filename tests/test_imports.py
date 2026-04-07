import importlib
import unittest
from pathlib import Path


class ImportTests(unittest.TestCase):
    def test_run_eval_imports(self):
        importlib.import_module("run_eval")

    def test_run_eval_uses_explicit_reexports(self):
        repo_root = Path(__file__).resolve().parents[1]
        source = (repo_root / "run_eval.py").read_text(encoding="utf-8")

        self.assertNotIn("import *", source)
        self.assertIn("__all__ =", source)

    def test_orenyl_server_imports(self):
        importlib.import_module("orenyl.server")


if __name__ == "__main__":
    unittest.main()
