import os
import tempfile
import unittest

from todocli import core


class CoreTest(unittest.TestCase):
    def test_add_and_done(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["TODO_FILE"] = os.path.join(d, "t.json")
            try:
                core.add("a")
                core.add("b")
                core.done(2)
                self.assertEqual([i["done"] for i in core.load()], [False, True])
            finally:
                del os.environ["TODO_FILE"]


if __name__ == "__main__":
    unittest.main()
