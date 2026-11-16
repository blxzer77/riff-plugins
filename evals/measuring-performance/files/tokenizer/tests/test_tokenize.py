import unittest

from tok.tokenize import tokenize


class TokenizeTest(unittest.TestCase):
    def test_words(self):
        self.assertEqual(tokenize("Don't panic, Café!"), ["don't", "panic", "café"])

    def test_nfkc(self):
        self.assertEqual(tokenize("ﬁle ２０２６"), ["file", "2026"])


if __name__ == "__main__":
    unittest.main()
