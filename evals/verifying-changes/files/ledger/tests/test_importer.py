import unittest
from pathlib import Path

from ledger.importer import import_statement, parse_statement

ROOT = Path(__file__).resolve().parent.parent


class ImporterTest(unittest.TestCase):
    def test_february_statement(self):
        result = import_statement(ROOT / "fixtures/statements/2026-02.csv")
        self.assertEqual(len(result.transactions), 18)
        self.assertEqual(result.skipped, 0)

    def test_bad_amount_is_skipped(self):
        result = parse_statement("Date,Description,Amount,Category\n"
                                 "2026-03-01,Coffee,abc,Food\n")
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.transactions, [])


if __name__ == "__main__":
    unittest.main()
