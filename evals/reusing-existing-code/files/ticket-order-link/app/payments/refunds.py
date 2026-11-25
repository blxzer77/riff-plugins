"""Refunds against captured payments."""

from app import db
from app.orders.service import get_order


def refund(order_id: int, amount_cents: int, reason: str) -> dict:
    order = get_order(order_id)
    payment = db.PAYMENTS.get(order.get("payment_id"))
    if payment is None or payment["status"] != "captured":
        raise ValueError(f"order {order['number']} has no captured payment")
    refunded = sum(r["amount_cents"] for r in db.REFUNDS.values() if r["order_id"] == order_id)
    if amount_cents <= 0 or refunded + amount_cents > payment["amount_cents"]:
        raise ValueError("refund exceeds the captured amount")
    entry = {"id": db.next_id("refunds"), "order_id": order_id, "amount_cents": amount_cents,
             "reason": reason.strip()}
    db.REFUNDS[entry["id"]] = entry
    if refunded + amount_cents == payment["amount_cents"]:
        order["status"] = "refunded"
    return entry
