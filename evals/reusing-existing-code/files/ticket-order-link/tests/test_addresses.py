import unittest

from app import db
from app.accounts.signup import create_customer
from app.addresses import book


class AddressBookTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")

    def add(self, **overrides):
        fields = {"name": "Erika Mustermann", "street": "Heidestraße 17", "postcode": "51147",
                  "city": "Köln"}
        fields.update(overrides)
        return book.add_address(self.customer["id"], **fields)

    def test_first_address_is_the_default(self):
        first, second = self.add(), self.add(street="Domkloster 4", postcode="50667")
        self.assertTrue(first["is_default"])
        self.assertFalse(second["is_default"])

    def test_postcode_must_match_the_country(self):
        with self.assertRaises(ValueError):
            self.add(postcode="5114")
        self.assertEqual(self.add(postcode="1010", city="Wien", country="AT")["postcode"], "1010")

    def test_we_only_ship_to_germany_austria_and_switzerland(self):
        with self.assertRaises(ValueError):
            self.add(country="FR", postcode="75001", city="Paris")

    def test_removing_the_default_promotes_another(self):
        first, second = self.add(), self.add(street="Domkloster 4", postcode="50667")
        book.remove_address(first["id"])
        self.assertTrue(book.get_address(second["id"])["is_default"])

    def test_unknown_customer(self):
        with self.assertRaises(LookupError):
            book.add_address(999, "Max", "Hauptstr. 1", "51147", "Köln")


if __name__ == "__main__":
    unittest.main()
