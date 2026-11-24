from app.discounts import calculate_vip_discount_cents


def build_invoice_summary(items: list[dict], *, is_vip: bool = False) -> dict:
    subtotal = sum(item["unit_cents"] * item["qty"] for item in items)
    discount = calculate_vip_discount_cents(subtotal, is_vip)
    return {
        "subtotal_cents": subtotal,
        "discount_cents": discount,
        "total_cents": subtotal - discount,
    }
