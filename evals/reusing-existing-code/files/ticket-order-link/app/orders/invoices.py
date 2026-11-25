"""Plain-text invoices, attached to the order confirmation."""

from app import config
from app.addresses.book import get_address
from app.catalog.pricing import format_eur
from app.catalog.products import get_product


def invoice_text(order: dict) -> str:
    address = get_address(order["address_id"])
    lines = [config.SHOP_NAME, "", f"Invoice for order {order['number']}", "",
             address["name"], address["street"], f"{address['postcode']} {address['city']}",
             address["country"], ""]
    for line in order["lines"]:
        lines.append(f"{line['qty']} x {get_product(line['sku']).name}")
    lines += ["", f"Subtotal: {format_eur(order['subtotal_cents'])}",
              f"Shipping: {format_eur(order['shipping_cents'])}"]
    if order["discount_cents"]:
        lines.append(f"Discount: {format_eur(-order['discount_cents'])}")
    lines.append(f"Total: {format_eur(order['total_cents'])}")
    if order["status"] == "awaiting_transfer":
        lines += ["", f"Please transfer the total within 14 days, quoting {order['number']} as the reference."]
    return "\n".join(lines)
