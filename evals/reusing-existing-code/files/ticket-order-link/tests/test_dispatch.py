import unittest

from app import db
from app.accounts import profile
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.cart import cart
from app.catalog import stock
from app.checkout.checkout import place_order
from app.notifications import outbox
from app.orders.service import mark_shipped


class ShippedMessagesTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        stock.reset()
        outbox.OUTBOX.clear()
        self.customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        address = add_address(self.customer["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
        basket = cart.new_cart(self.customer["id"])
        cart.add_item(basket["id"], "LMN-4001")
        self.order = place_order(basket["id"], address["id"], "card")

    def test_email_only_without_text_updates(self):
        mark_shipped(self.order["id"], "PX123456")
        self.assertEqual([m["channel"] for m in outbox.OUTBOX], ["email"])
        self.assertIn("https://track.courier.example/PX123456", outbox.OUTBOX[0]["body"])

    def test_text_update_goes_to_the_mobile_number(self):
        profile.update_mobile(self.customer["id"], "0151 2345 6789")
        profile.set_sms_updates(self.customer["id"], True)
        mark_shipped(self.order["id"], "PX123456")
        texts = [m for m in outbox.OUTBOX if m["channel"] == "sms"]
        self.assertEqual(texts[0]["to"], "+4915123456789")


if __name__ == "__main__":
    unittest.main()
