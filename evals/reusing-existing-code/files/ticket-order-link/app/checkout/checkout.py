"""Turning a cart into an order."""

from app import db
from app.addresses.book import get_address
from app.cart.cart import totals
from app.catalog import stock
from app.checkout.vouchers import discount_cents
from app.orders.service import create_order
from app.payments.gateway import charge


def place_order(cart_id: int, address_id: int, payment_method: str, voucher: str | None = None) -> dict:
    cart = db.CARTS[cart_id]
    if not cart["lines"]:
        raise ValueError("the cart is empty")
    address = get_address(address_id)
    if address["customer_id"] != cart["customer_id"]:
        raise PermissionError("address belongs to another customer")
    sums = totals(cart_id, address["country"])
    discount = discount_cents(voucher, sums["subtotal_cents"]) if voucher else 0
    lines = [{"sku": sku, "qty": qty} for sku, qty in cart["lines"].items()]
    for line in lines:
        stock.reserve(line["sku"], line["qty"])
    order = create_order(cart["customer_id"], address_id, lines,
                         sums["subtotal_cents"], sums["shipping_cents"], discount)
    payment = charge(order["total_cents"], payment_method, order["number"])
    if payment["status"] == "declined":
        for line in lines:
            stock.release(line["sku"], line["qty"])
        order["status"] = "payment_failed"
        return order
    order["status"] = "paid" if payment["status"] == "captured" else "awaiting_transfer"
    order["payment_id"] = payment["id"]
    del db.CARTS[cart_id]
    return order
