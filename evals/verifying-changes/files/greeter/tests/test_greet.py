import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from greeter import greet  # noqa: E402


class GreetTest(unittest.TestCase):
    def test_greets(self):
        self.assertTrue(greet("ana").startswith("Hello, "))


if __name__ == "__main__":
    unittest.main()
