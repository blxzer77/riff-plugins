import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.cart import cart
from app.catalog import stock
from app.checkout.checkout import place_order


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        stock.reset()
        customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        self.address = add_address(customer["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
        self.cart = cart.new_cart(customer["id"])

    def test_paid_order_reserves_stock_and_empties_the_cart(self):
        cart.add_item(self.cart["id"], "LMN-1002", qty=2)
        order = place_order(self.cart["id"], self.address["id"], "card")
        self.assertEqual(order["status"], "paid")
        self.assertEqual(order["number"], "A-1001")
        self.assertEqual(stock.available("LMN-1002"), 1)
        self.assertNotIn(self.cart["id"], db.CARTS)

    def test_declined_payment_releases_stock(self):
        cart.add_item(self.cart["id"], "LMN-3001", qty=3)
        order = place_order(self.cart["id"], self.address["id"], "card")
        self.assertEqual(order["status"], "payment_failed")
        self.assertEqual(stock.available("LMN-3001"), 4)

    def test_invoice_orders_keep_their_stock_until_the_transfer(self):
        cart.add_item(self.cart["id"], "LMN-1001")
        order = place_order(self.cart["id"], self.address["id"], "invoice")
        self.assertEqual(order["status"], "awaiting_transfer")
        self.assertEqual(stock.available("LMN-1001"), 11)

    def test_empty_cart(self):
        with self.assertRaises(ValueError):
            place_order(self.cart["id"], self.address["id"], "card")


if __name__ == "__main__":
    unittest.main()
