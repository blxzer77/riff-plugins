import unittest

from app.catalog.pricing import format_eur, gross_cents
from app.catalog.products import get_product
from app.catalog.search import search


class PricingTest(unittest.TestCase):
    def test_german_price_is_the_catalog_price(self):
        self.assertEqual(gross_cents(get_product("LMN-2001"), "DE"), 7900)

    def test_austrian_vat(self):
        # 7900 / 1.19 = 6638.66 -> 6639 net, * 1.20 = 7966.8 -> 7967
        self.assertEqual(gross_cents(get_product("LMN-2001"), "AT"), 7967)

    def test_format(self):
        self.assertEqual(format_eur(123456), "1.234,56 €")
        self.assertEqual(format_eur(-500), "-5,00 €")


class SearchTest(unittest.TestCase):
    def test_finds_active_products_by_words(self):
        self.assertEqual([p.sku for p in search("oslo black")], ["LMN-1002"])
        self.assertEqual(search("malmo"), [])


if __name__ == "__main__":
    unittest.main()
