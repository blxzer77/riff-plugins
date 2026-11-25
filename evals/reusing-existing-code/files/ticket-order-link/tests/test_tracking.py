import unittest

from app.shipping.tracking import parse_status_event, tracking_url


class TrackingTest(unittest.TestCase):
    def test_status_event(self):
        event = {"parcel": {"number": "PX1"}, "event": {"code": "DL"}}
        self.assertEqual(parse_status_event(event), ("PX1", "delivered"))

    def test_unknown_code(self):
        with self.assertRaises(ValueError):
            parse_status_event({"parcel": {"number": "PX1"}, "event": {"code": "ZZ"}})

    def test_url(self):
        self.assertEqual(tracking_url("PX1"), "https://track.courier.example/PX1")


if __name__ == "__main__":
    unittest.main()
