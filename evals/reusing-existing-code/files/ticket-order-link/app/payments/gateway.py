"""Client for the payment provider. Outside production, charges are simulated."""

from app import db

METHODS = ("card", "paypal", "invoice")
# The provider's sandbox declines charges above this amount.
SANDBOX_DECLINE_ABOVE_CENTS = 50_000


def charge(amount_cents: int, method: str, reference: str) -> dict:
    if method not in METHODS:
        raise ValueError(f"unknown payment method {method!r}")
    if method == "invoice":
        status = "pending"  # paid later by bank transfer, see payments/transfers.py
    else:
        status = "declined" if amount_cents > SANDBOX_DECLINE_ABOVE_CENTS else "captured"
    payment = {"id": db.next_id("payments"), "amount_cents": amount_cents, "method": method,
               "reference": reference, "status": status}
    db.PAYMENTS[payment["id"]] = payment
    return payment
