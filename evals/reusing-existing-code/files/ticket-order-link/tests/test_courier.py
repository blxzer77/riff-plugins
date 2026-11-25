import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.orders.service import create_order
from app.shipping.courier import build_label


class LabelTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        self.address = add_address(self.customer["id"], "Erika Mustermann", "Heidestraße 17",
                                   "51147", "Köln")

    def test_label_has_recipient_and_weight(self):
        order = create_order(self.customer["id"], self.address["id"],
                             [{"sku": "LMN-2001", "qty": 2}], 15800, 0)
        label = build_label(order)
        self.assertEqual(label["reference"], order["number"])
        self.assertEqual(label["recipient_name"], "Erika Mustermann")
        self.assertEqual(label["recipient_postcode"], "51147")
        self.assertEqual(label["recipient_country"], "DE")
        self.assertEqual(label["weight_grams"], 350 + 2 * 1200)


if __name__ == "__main__":
    unittest.main()
