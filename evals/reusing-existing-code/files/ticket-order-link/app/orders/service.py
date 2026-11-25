"""Orders after checkout."""

from datetime import datetime, timezone

from app import db
from app.catalog import stock
from app.notifications.dispatch import order_shipped
from app.orders.numbers import next_order_number


def create_order(customer_id: int, address_id: int, lines: list[dict], subtotal_cents: int,
                 shipping_cents: int, discount_cents: int = 0) -> dict:
    order = {
        "id": db.next_id("orders"),
        "number": next_order_number(),
        "customer_id": customer_id,
        "address_id": address_id,
        "lines": lines,
        "subtotal_cents": subtotal_cents,
        "shipping_cents": shipping_cents,
        "discount_cents": discount_cents,
        "total_cents": subtotal_cents + shipping_cents - discount_cents,
        "status": "new",
        "created_at": datetime.now(timezone.utc),
        "tracking_number": None,
    }
    db.ORDERS[order["id"]] = order
    return order


def get_order(order_id: int) -> dict:
    try:
        return db.ORDERS[order_id]
    except KeyError:
        raise LookupError(f"no order {order_id}") from None


def mark_shipped(order_id: int, tracking_number: str) -> dict:
    order = get_order(order_id)
    if order["status"] != "paid":
        raise ValueError(f"order {order['number']} is {order['status']}, not paid")
    order["status"] = "shipped"
    order["tracking_number"] = tracking_number
    order_shipped(order)
    return order


def cancel_order(order_id: int) -> dict:
    """Cancel an order that was never paid. Paid orders are refunded instead."""
    order = get_order(order_id)
    if order["status"] not in ("new", "awaiting_transfer", "payment_failed"):
        raise ValueError(f"order {order['number']} is {order['status']}; refund it instead")
    if order["status"] != "payment_failed":
        for line in order["lines"]:
            stock.release(line["sku"], line["qty"])
    order["status"] = "cancelled"
    return order
