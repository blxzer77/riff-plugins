"""Bank transfers for orders paid by invoice: match each incoming transfer to its order."""

import re

from app import db
from app.orders.numbers import PREFIX

# How customers write our references into a transfer or an email: any case, the dash
# replaced by a space, a dot, a slash or a word processor's en dash, or left out; never
# inside a longer code ("CA-1001") or number.
_LETTERS = re.escape(PREFIX.rstrip("-"))
_REFERENCE = re.compile(rf"(?<![A-Z0-9]){_LETTERS}\s*[-–—./]?\s*(\d{{4,7}})(?!\d)")


def reference_in(text: str) -> str | None:
    """The first of our references in free text, as we print it ("a 1001" -> "A-1001")."""
    match = _REFERENCE.search(text.upper())
    return f"{PREFIX}{match.group(1)}" if match else None


def match_transfer(transfer: dict) -> dict | None:
    """The order waiting for this transfer, if its reference and amount fit."""
    reference = reference_in(transfer["remittance"])
    order = next((o for o in db.ORDERS.values() if o["number"] == reference), None)
    if order is None or order["status"] != "awaiting_transfer":
        return None
    return order if order["total_cents"] == transfer["amount_cents"] else None


def book_transfers(transfers: list[dict]) -> dict:
    """Mark the orders the day's transfers pay for as paid; the rest go to manual review."""
    paid, review = [], []
    for transfer in transfers:
        order = match_transfer(transfer)
        if order is None:
            review.append(transfer)
            continue
        order["status"] = "paid"
        db.PAYMENTS[order["payment_id"]]["status"] = "captured"
        paid.append(order["number"])
    return {"paid": paid, "review": review}
