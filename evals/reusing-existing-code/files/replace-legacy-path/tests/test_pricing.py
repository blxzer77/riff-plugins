import unittest

from app.checkout import checkout_total_cents
from app.discounts import calculate_vip_discount_cents
from app.invoices import build_invoice_summary


class PricingTest(unittest.TestCase):
    def test_non_vip_and_vip_checkout(self):
        items = [{"sku": "A", "unit_cents": 1000, "qty": 2}]
        self.assertEqual(checkout_total_cents(items, is_vip=False), 2000)
        self.assertEqual(checkout_total_cents(items, is_vip=True), 1800)

    def test_invoice_summary(self):
        items = [{"sku": "A", "unit_cents": 1000, "qty": 4}]
        summary = build_invoice_summary(items, is_vip=True)
        self.assertEqual(summary, {"subtotal_cents": 4000, "discount_cents": 400, "total_cents": 3600})

    def test_discount_helper(self):
        self.assertEqual(calculate_vip_discount_cents(5000, True), 500)


if __name__ == "__main__":
    unittest.main()
