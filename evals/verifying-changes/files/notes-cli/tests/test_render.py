import json
import unittest

from notes.render import render

NOTES = [{"id": 1, "title": "Groceries", "tags": ["home"]}]


class RenderTest(unittest.TestCase):
    def test_json(self):
        self.assertEqual(json.loads(render(NOTES, "json")), NOTES)

    def test_table(self):
        self.assertIn("Groceries", render(NOTES, "table"))
        self.assertTrue(render(NOTES, "table").startswith("ID"))


if __name__ == "__main__":
    unittest.main()
