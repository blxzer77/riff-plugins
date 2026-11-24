import unittest

from app.api.teams import TEAMS, create_team
from app.core.identity import canonicalize_account_slug


class TeamsTest(unittest.TestCase):
    def setUp(self):
        TEAMS.clear()

    def test_slug_normalization(self):
        self.assertEqual(canonicalize_account_slug("  Café Ops!! "), "cafe-ops")
        self.assertEqual(canonicalize_account_slug("a" * 39 + "-xyz", max_length=40), "a" * 39)
        with self.assertRaises(ValueError):
            canonicalize_account_slug("ab")

    def test_create_team(self):
        team = create_team("Core Infra", "Lead@Example.COM")
        self.assertEqual(team["slug"], "core-infra")
        self.assertEqual(team["owner_email"], "lead@example.com")


if __name__ == "__main__":
    unittest.main()
