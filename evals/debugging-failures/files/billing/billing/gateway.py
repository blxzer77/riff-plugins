"""Thin client for the payment gateway (the HTTP part is stubbed out here).

Every failure from the gateway is raised as GatewayError. `transient` is True when
the gateway says the same request may succeed if sent again (dropped connection,
gateway overload); it is False for answers about the payment itself (card
declined, insufficient funds, invalid amount). Charges carry an idempotency key, so
sending the same key twice never charges twice.
"""


class GatewayError(Exception):
    def __init__(self, code: str, transient: bool):
        super().__init__(f"{code} (transient={transient})")
        self.code = code
        self.transient = transient


class Gateway:
    def charge(self, customer_id: str, amount_cents: int, idempotency_key: str) -> str:
        raise NotImplementedError("network call; replaced by a fake in tests")
