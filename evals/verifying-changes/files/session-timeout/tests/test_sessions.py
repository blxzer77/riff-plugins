import unittest

from app.sessions import new_session
from app.settings import SESSION_TTL_MINUTES


class SessionTest(unittest.TestCase):
    def test_cookie_lifetime_matches_setting(self):
        s = new_session("u1", now=0)
        self.assertEqual(s["cookie"]["max_age"], SESSION_TTL_MINUTES * 60)


if __name__ == "__main__":
    unittest.main()
