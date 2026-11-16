import json
import unittest

from reports.upload import upload_report


class FakeResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class UploadTest(unittest.TestCase):
    def test_puts_json(self):
        seen = []

        def opener(request, timeout):
            seen.append(request)
            return FakeResponse()

        self.assertEqual(upload_report({"users": 3}, url="http://store.invalid/r", opener=opener), 201)
        self.assertEqual(seen[0].get_method(), "PUT")
        self.assertEqual(json.loads(seen[0].data), {"users": 3})


if __name__ == "__main__":
    unittest.main()
