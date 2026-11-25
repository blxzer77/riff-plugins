import unittest

from app import db
from app.accounts.sessions import current_customer, login, logout
from app.accounts.signup import create_customer


class SessionTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        create_customer("erika@example.com", "lampenfieber", "Erika")

    def test_login_with_any_email_case(self):
        token = login("ERIKA@example.com", "lampenfieber")
        self.assertEqual(current_customer(token)["email"], "erika@example.com")

    def test_wrong_password(self):
        with self.assertRaises(PermissionError):
            login("erika@example.com", "lampenfieber!")

    def test_logout(self):
        token = login("erika@example.com", "lampenfieber")
        logout(token)
        self.assertIsNone(current_customer(token))


if __name__ == "__main__":
    unittest.main()
