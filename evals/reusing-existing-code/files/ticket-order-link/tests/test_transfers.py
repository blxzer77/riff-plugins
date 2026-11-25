import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.cart import cart
from app.catalog import stock
from app.checkout.checkout import place_order
from app.payments.transfers import book_transfers, reference_in


class ReferenceTest(unittest.TestCase):
    def test_spellings_from_bank_transfers(self):
        for text in ("A-1001", "RECHNUNG A 1001", "a1001 danke", "Nr. A.1001", "A–1001",
                     "#A - 1001", "Bestellung A/1001 vom 3.11."):
            with self.subTest(text=text):
                self.assertEqual(reference_in(text), "A-1001")

    def test_not_ours(self):
        for text in ("CA-1001", "A-12", "A-10012345", "Miete November", ""):
            with self.subTest(text=text):
                self.assertIsNone(reference_in(text))


class BookingTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        stock.reset()
        customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        address = add_address(customer["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
        basket = cart.new_cart(customer["id"])
        cart.add_item(basket["id"], "LMN-2001")
        self.order = place_order(basket["id"], address["id"], "invoice")

    def test_invoice_orders_wait_for_the_transfer(self):
        self.assertEqual(self.order["status"], "awaiting_transfer")
        result = book_transfers([{"remittance": "RECHNUNG A 1001", "amount_cents": 7900}])
        self.assertEqual(result, {"paid": ["A-1001"], "review": []})
        self.assertEqual(self.order["status"], "paid")

    def test_wrong_amount_or_unknown_reference_goes_to_review(self):
        transfers = [{"remittance": "A-1001", "amount_cents": 7000},
                     {"remittance": "A-1999", "amount_cents": 7900}]
        self.assertEqual(book_transfers(transfers), {"paid": [], "review": transfers})
        self.assertEqual(self.order["status"], "awaiting_transfer")


if __name__ == "__main__":
    unittest.main()
