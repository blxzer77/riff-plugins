import unittest

from app.notifications import outbox
from app.notifications.sms import segments, send_sms, to_msisdn


class MsisdnTest(unittest.TestCase):
    def test_spellings_customers_use(self):
        for raw in ("0151 2345 6789", "0151/23456789", "+49 151 2345 6789",
                    "+49 (0)151 2345 6789", "0049 151 23456789", "(0151) 234-56789"):
            with self.subTest(raw=raw):
                self.assertEqual(to_msisdn(raw), "+4915123456789")

    def test_national_numbers_take_the_calling_code_of_the_region(self):
        self.assertEqual(to_msisdn("0664 1234567", region="AT"), "+436641234567")

    def test_rejects_what_the_gateway_rejects(self):
        for raw in ("", "12345", "call me", "+49"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    to_msisdn(raw)


class SendTest(unittest.TestCase):
    def setUp(self):
        outbox.OUTBOX.clear()

    def test_send_records_the_message(self):
        send_sms("+4915123456789", "Hello")
        self.assertEqual(outbox.OUTBOX, [{"channel": "sms", "to": "+4915123456789",
                                          "subject": None, "body": "Hello"}])

    def test_send_needs_a_normalized_number(self):
        with self.assertRaises(ValueError):
            send_sms("0151 2345 6789", "Hello")

    def test_segments(self):
        self.assertEqual(segments("x" * 160), 1)
        self.assertEqual(segments("x" * 161), 2)


if __name__ == "__main__":
    unittest.main()
