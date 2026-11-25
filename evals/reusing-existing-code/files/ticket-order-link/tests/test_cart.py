import unittest

from app import db
from app.cart import cart


class CartTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.cart = cart.new_cart(customer_id=1)

    def test_totals_include_shipping(self):
        cart.add_item(self.cart["id"], "LMN-2001")
        self.assertEqual(cart.totals(self.cart["id"], "DE"),
                         {"subtotal_cents": 7900, "shipping_cents": 0, "total_cents": 7900})

    def test_small_orders_pay_shipping(self):
        cart.add_item(self.cart["id"], "LMN-4001", qty=3)
        self.assertEqual(cart.totals(self.cart["id"], "DE")["shipping_cents"], 490)

    def test_discontinued_products_cannot_be_added(self):
        with self.assertRaises(ValueError):
            cart.add_item(self.cart["id"], "LMN-9001")


if __name__ == "__main__":
    unittest.main()
