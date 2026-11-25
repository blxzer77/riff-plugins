import unittest

from app.shipping.rates import shipping_cents


class RatesTest(unittest.TestCase):
    def test_free_shipping_in_germany_from_75_euros(self):
        self.assertEqual(shipping_cents("DE", 1500, 7500), 0)
        self.assertEqual(shipping_cents("DE", 1500, 7499), 490)

    def test_weight_bands(self):
        self.assertEqual(shipping_cents("AT", 2001, 1000), 1490)
        self.assertEqual(shipping_cents("CH", 31500, 1000), 3990)

    def test_too_heavy_or_not_shipped(self):
        with self.assertRaises(ValueError):
            shipping_cents("DE", 40000, 0)
        with self.assertRaises(ValueError):
            shipping_cents("FR", 1000, 0)


if __name__ == "__main__":
    unittest.main()
