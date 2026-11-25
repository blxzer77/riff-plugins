import unittest

from app import db
from app.accounts.sessions import login
from app.api.router import dispatch


class ApiTest(unittest.TestCase):
    def setUp(self):
        db.reset()

    def signed_in(self):
        status, _ = dispatch("POST", "/signup", {"email": "erika@example.com",
                                                 "password": "lampenfieber", "name": "Erika"})
        self.assertEqual(status, 201)
        return login("erika@example.com", "lampenfieber")

    def test_private_routes_need_a_session(self):
        self.assertEqual(dispatch("GET", "/me/addresses")[0], 401)

    def test_add_and_list_addresses(self):
        token = self.signed_in()
        status, _ = dispatch("POST", "/me/addresses", {"name": "Erika", "street": "Heidestraße 17",
                                                       "postcode": "51147", "city": "Köln"}, token)
        self.assertEqual(status, 201)
        status, body = dispatch("GET", "/me/addresses", token=token)
        self.assertEqual([a["city"] for a in body["data"]], ["Köln"])

    def test_invalid_mobile_number(self):
        token = self.signed_in()
        self.assertEqual(dispatch("PUT", "/me/mobile", {"mobile": "call me"}, token)[0], 422)

    def test_unknown_route(self):
        self.assertEqual(dispatch("GET", "/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
