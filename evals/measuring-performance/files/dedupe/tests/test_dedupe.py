import unittest

from textutil.dedupe import dedupe, dedupe_fast
from textutil.search import unique_terms


class DedupeTest(unittest.TestCase):
    def test_removes_repeats(self):
        self.assertEqual(sorted(dedupe([3, 1, 3, 2, 1])), [1, 2, 3])
        self.assertEqual(sorted(dedupe_fast([3, 1, 3, 2, 1])), [1, 2, 3])

    def test_unique_terms(self):
        self.assertEqual(sorted(unique_terms("Red red blue")), ["blue", "red"])


if __name__ == "__main__":
    unittest.main()
