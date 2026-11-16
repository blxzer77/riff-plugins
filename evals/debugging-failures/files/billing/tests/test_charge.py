import unittest

from billing.charge import charge_with_retry
from billing.gateway import GatewayError


class FakeGateway:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def charge(self, customer_id, amount_cents, idempotency_key):
        self.calls.append(idempotency_key)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class ChargeWithRetryTest(unittest.TestCase):
    def test_success_first_try(self):
        gw = FakeGateway(["ch_1"])
        self.assertEqual(charge_with_retry(gw, "c1", 500, sleep=lambda s: None), "ch_1")

    def test_retries_timeout_with_same_key(self):
        gw = FakeGateway([TimeoutError(), "ch_2"])
        self.assertEqual(charge_with_retry(gw, "c1", 500, sleep=lambda s: None), "ch_2")
        self.assertEqual(len(set(gw.calls)), 1)

    def test_gives_up_after_attempts(self):
        gw = FakeGateway([TimeoutError()] * 3)
        with self.assertRaises(TimeoutError):
            charge_with_retry(gw, "c1", 500, sleep=lambda s: None)

    def test_decline_is_raised(self):
        gw = FakeGateway([GatewayError("card_declined", transient=False)])
        with self.assertRaises(GatewayError):
            charge_with_retry(gw, "c1", 500, sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
