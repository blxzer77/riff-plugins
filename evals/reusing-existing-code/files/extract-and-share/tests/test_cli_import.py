import tempfile
import unittest
from pathlib import Path

from app.cli_import import run_cli
from app.store import ORDERS_DB


class CliImportTest(unittest.TestCase):
    def setUp(self):
        ORDERS_DB.clear()

    def test_cli_import_valid_and_bad_rows(self):
        csv_text = (
            "order_id,sku,qty,unit_price,ordered_on\n"
            "ord-1,ab-1234,2,12.50,2026-11-01\n"
            "ord-2,BAD,1,5.00,2026-11-01\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "orders.csv"
            p.write_text(csv_text, encoding="utf-8")
            code = run_cli(str(p))
        self.assertEqual(code, 0)
        self.assertIn("ord-1", ORDERS_DB)
        self.assertEqual(ORDERS_DB["ord-1"]["total_cents"], 2500)
        self.assertNotIn("ord-2", ORDERS_DB)


if __name__ == "__main__":
    unittest.main()
