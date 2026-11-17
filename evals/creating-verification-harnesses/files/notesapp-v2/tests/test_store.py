import tempfile
import unittest

from notesapp.store import Store


class StoreTest(unittest.TestCase):
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(d)
            s.add("Groceries", "milk")
            s.add("Roadmap")
            self.assertEqual([n["title"] for n in s.search("road")], ["Roadmap"])
            self.assertEqual([n["title"] for n in s.search("MILK")], ["Groceries"])

    def test_title_required(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                Store(d).add("  ")


if __name__ == "__main__":
    unittest.main()
