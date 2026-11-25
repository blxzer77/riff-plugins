import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.cart import cart
from app.catalog import stock
from app.checkout.checkout import place_order
from app.payments.refunds import refund


class RefundTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        stock.reset()
        customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        address = add_address(customer["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
        basket = cart.new_cart(customer["id"])
        cart.add_item(basket["id"], "LMN-2001")
        self.order = place_order(basket["id"], address["id"], "paypal")

    def test_partial_then_full_refund(self):
        refund(self.order["id"], 2900, "scratched shade")
        self.assertEqual(self.order["status"], "paid")
        refund(self.order["id"], 5000, "returned")
        self.assertEqual(self.order["status"], "refunded")

    def test_cannot_refund_more_than_was_paid(self):
        with self.assertRaises(ValueError):
            refund(self.order["id"], 7901, "too much")


if __name__ == "__main__":
    unittest.main()
