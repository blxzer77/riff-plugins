import unittest

from app import db
from app.accounts import profile
from app.accounts.signup import create_customer


class ProfileTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        self.customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")

    def test_mobile_number_enables_text_updates(self):
        customer = profile.update_mobile(self.customer["id"], "0151 2345 6789")
        self.assertEqual(customer["mobile"], "+4915123456789")
        profile.set_sms_updates(customer["id"], True)
        self.assertTrue(customer["sms_updates"])

    def test_text_updates_need_a_mobile_number(self):
        with self.assertRaises(ValueError):
            profile.set_sms_updates(self.customer["id"], True)

    def test_removing_the_mobile_number_stops_text_updates(self):
        profile.update_mobile(self.customer["id"], "0151 2345 6789")
        profile.set_sms_updates(self.customer["id"], True)
        customer = profile.remove_mobile(self.customer["id"])
        self.assertIsNone(customer["mobile"])
        self.assertFalse(customer["sms_updates"])

    def test_rename(self):
        self.assertEqual(profile.rename(self.customer["id"], "  Erika M. ")["name"], "Erika M.")


if __name__ == "__main__":
    unittest.main()
