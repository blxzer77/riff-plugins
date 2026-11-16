import os
import tempfile
import unittest

from contacts.importer import Contact, load, parse_line


class ParseLineTest(unittest.TestCase):
    def test_simple_row(self):
        self.assertEqual(parse_line("Ann Lee,Ann@Example.com,Initech\n"),
                         Contact("Ann Lee", "ann@example.com", "Initech"))

    def test_rejects_bad_email(self):
        with self.assertRaises(ValueError):
            parse_line("Bob,not-an-email,Initech\n")


class LoadTest(unittest.TestCase):
    def test_skips_header_and_blank_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("name,email,company\nAnn Lee,ann@example.com,Initech\n\n")
        try:
            self.assertEqual(len(load(f.name)), 1)
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
