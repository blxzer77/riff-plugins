import unittest

from calc.money import add, fmt


class MoneyTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_fmt(self):
        self.assertEqual(fmt(1234), "$12.34")
        self.assertEqual(fmt(5), "$0.05")


if __name__ == "__main__":
    unittest.main()
