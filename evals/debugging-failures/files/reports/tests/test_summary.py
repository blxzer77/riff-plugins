import unittest

from reports.summary import summarize


class SummarizeTest(unittest.TestCase):
    def test_totals_per_region(self):
        rows = [{"region": "EU", "amount": 300}, {"region": "US", "amount": 200},
                {"region": "EU", "amount": 100}]
        self.assertEqual(summarize(rows), {"EU": 400, "US": 200})


if __name__ == "__main__":
    unittest.main()
