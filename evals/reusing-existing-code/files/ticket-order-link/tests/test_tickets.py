import unittest

from app import db
from app.accounts.signup import create_customer
from app.notifications import outbox
from app.support import tickets


class TicketTest(unittest.TestCase):
    def setUp(self):
        db.reset()
        outbox.OUTBOX.clear()
        self.customer = create_customer("erika@example.com", "lampenfieber", "Erika Mustermann")

    def test_open_reply_close(self):
        ticket = tickets.open_ticket(self.customer["id"], "Lampe flackert", "Seit gestern flackert sie.")
        self.assertEqual(ticket["status"], "open")
        tickets.reply(ticket["id"], "Jonas", "Bitte tauschen Sie das Leuchtmittel.")
        self.assertEqual(ticket["status"], "waiting")
        self.assertEqual(outbox.OUTBOX[-1]["subject"], "Re: Lampe flackert")
        tickets.close(ticket["id"])
        with self.assertRaises(ValueError):
            tickets.reply(ticket["id"], "Jonas", "Noch etwas?")

    def test_subject_and_message_are_required(self):
        with self.assertRaises(ValueError):
            tickets.open_ticket(self.customer["id"], " ", "Hallo")


if __name__ == "__main__":
    unittest.main()
