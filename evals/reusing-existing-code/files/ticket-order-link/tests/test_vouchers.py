import unittest
from datetime import date

from app.checkout.vouchers import discount_cents

TODAY = date(2026, 11, 2)


class VoucherTest(unittest.TestCase):
    def test_percent_voucher(self):
        self.assertEqual(discount_cents("welcome10", 8000, today=TODAY), 800)

    def test_fixed_voucher(self):
        self.assertEqual(discount_cents("LIGHT5", 2500, today=TODAY), 500)

    def test_minimum_order_and_expiry(self):
        with self.assertRaises(ValueError):
            discount_cents("WELCOME10", 4999, today=TODAY)
        with self.assertRaises(ValueError):
            discount_cents("LIGHT5", 3000, today=date(2027, 1, 1))


if __name__ == "__main__":
    unittest.main()
