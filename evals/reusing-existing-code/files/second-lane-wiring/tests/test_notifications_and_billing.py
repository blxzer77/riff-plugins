import unittest

from app.billing.invoices import mark_invoice_paid
from app.billing.renewals import PaymentDeclinedError, process_renewal
from app.notifications.dispatch import DISPATCH_LOG, OPTED_OUT_USERS, send_notification


class BillingAndNotificationsTest(unittest.TestCase):
    def setUp(self):
        DISPATCH_LOG.clear()
        OPTED_OUT_USERS.clear()

    def test_invoice_paid_notifies(self):
        res = mark_invoice_paid("inv_1", "u_1", "$20.00")
        self.assertEqual(res["status"], "paid")
        self.assertEqual(len(DISPATCH_LOG), 1)
        self.assertEqual(DISPATCH_LOG[0]["event"], "invoice_paid")

    def test_opt_out_blocks_non_critical(self):
        OPTED_OUT_USERS.add("u_2")
        out = send_notification("u_2", "trial_ending", {"plan": "pro", "days": 3})
        self.assertIsNone(out)
        self.assertEqual(DISPATCH_LOG, [])

    def test_renewal_success_and_decline(self):
        sub = {"subscription_id": "sub_1", "user_id": "u_1", "amount": "$15.00", "status": "active"}
        res = process_renewal(sub, lambda _id, _amt: None)
        self.assertEqual(res["status"], "active")

        def fail(_id, _amt):
            raise PaymentDeclinedError("card declined")

        res2 = process_renewal(sub, fail)
        self.assertEqual(res2["status"], "past_due")
        self.assertEqual(sub["status"], "past_due")


if __name__ == "__main__":
    unittest.main()
