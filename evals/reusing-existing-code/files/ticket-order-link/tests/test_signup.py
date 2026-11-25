import unittest

from app import db
from app.accounts.signup import create_customer


class SignupTest(unittest.TestCase):
    def setUp(self):
        db.reset()

    def test_creates_customer_with_normalized_email(self):
        customer = create_customer("  Erika@Example.COM ", "lampenfieber", "Erika Mustermann")
        self.assertEqual(customer["email"], "erika@example.com")
        self.assertIsNone(customer["mobile"])
        self.assertFalse(customer["sms_updates"])

    def test_rejects_duplicate_email(self):
        create_customer("erika@example.com", "lampenfieber", "Erika")
        with self.assertRaises(ValueError):
            create_customer("ERIKA@example.com", "lampenfieber", "Erika")

    def test_rejects_weak_password(self):
        with self.assertRaises(ValueError):
            create_customer("erika@example.com", "1234567890", "Erika")
        with self.assertRaises(ValueError):
            create_customer("erika@example.com", "short", "Erika")


if __name__ == "__main__":
    unittest.main()
