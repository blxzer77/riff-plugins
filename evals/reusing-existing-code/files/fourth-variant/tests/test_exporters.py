import unittest
from datetime import date

from app.exporters import export_customers_csv, export_orders_csv, export_refunds_csv
from app.models import Customer, Order, Refund


class ExportersTest(unittest.TestCase):
    def test_export_orders(self):
        out = export_orders_csv([Order("o1", "c1", 1250, date(2026, 11, 1))])
        self.assertEqual(out["filename"], "orders.csv")
        self.assertEqual(out["row_count"], 1)
        self.assertEqual(out["total_amount"], "12.50")
        self.assertTrue(out["content"].startswith("\ufefforder_id,customer_id,total,placed_at\n"))
        self.assertIn("o1,c1,12.50,2026-11-01\n", out["content"])

    def test_export_customers(self):
        out = export_customers_csv([Customer("c1", "a@b.com", 500, date(2026, 1, 2))])
        self.assertEqual(out["filename"], "customers.csv")
        self.assertEqual(out["total_amount"], "5.00")

    def test_export_refunds(self):
        out = export_refunds_csv([])
        self.assertEqual(out["filename"], "refunds.csv")
        self.assertEqual(out["row_count"], 0)
        self.assertEqual(out["total_amount"], "0.00")


if __name__ == "__main__":
    unittest.main()
