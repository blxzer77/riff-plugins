import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("publish", Path(__file__).resolve().parent.parent / "scripts" / "publish.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class BumpTest(unittest.TestCase):
    def test_patch(self):
        self.assertEqual(publish.bump("0.4.0"), "0.4.1")
        self.assertEqual(publish.bump("1.9.9"), "1.9.10")


if __name__ == "__main__":
    unittest.main()
