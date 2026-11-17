import unittest

from uploader.session import Session, UploadError
from uploader.store import MemoryStore


class SessionTest(unittest.TestCase):
    def test_upload_publishes(self):
        store = MemoryStore()
        s = Session(store, "report.pdf")
        s.start()
        s.write(b"abc")
        s.publish()
        s.mark_committed()
        self.assertEqual(store.published["report.pdf"], b"abc")
        self.assertEqual(store.temp, {})

    def test_cancel_while_uploading(self):
        store = MemoryStore()
        s = Session(store, "report.pdf")
        s.start()
        s.cancel()
        self.assertEqual(s.state, "cancelled")
        self.assertEqual(store.published, {})

    def test_cannot_cancel_twice(self):
        s = Session(MemoryStore(), "x")
        s.start()
        s.cancel()
        with self.assertRaises(UploadError):
            s.cancel()


if __name__ == "__main__":
    unittest.main()
