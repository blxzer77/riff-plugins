from app.discounts import calculate_vip_discount_cents


def checkout_total_cents(items: list[dict], *, is_vip: bool = False) -> int:
    subtotal = sum(item["unit_cents"] * item["qty"] for item in items)
    discount = calculate_vip_discount_cents(subtotal, is_vip)
    return subtotal - discount
