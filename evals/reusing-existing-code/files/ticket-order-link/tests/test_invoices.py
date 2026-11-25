import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses.book import add_address
from app.orders.invoices import invoice_text
from app.orders.service import create_order


class InvoiceTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")
        address = add_address(customer["id"], "Erika Mustermann", "Heidestraße 17", "51147", "Köln")
        self.order = create_order(customer["id"], address["id"], [{"sku": "LMN-4001", "qty": 2}],
                                  1380, 490, 500)

    def test_invoice_lists_lines_and_totals(self):
        text = invoice_text(self.order)
        self.assertIn("Invoice for order A-1001", text)
        self.assertIn("2 x LED bulb E27 2700K", text)
        self.assertIn("Discount: -5,00 €", text)
        self.assertTrue(text.endswith("Total: 13,70 €"))


if __name__ == "__main__":
    unittest.main()
