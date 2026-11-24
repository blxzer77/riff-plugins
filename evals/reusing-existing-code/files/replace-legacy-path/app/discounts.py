FLAT_VIP_RATE = 0.10


def calculate_vip_discount_cents(subtotal_cents: int, is_vip: bool) -> int:
    if not is_vip:
        return 0
    return round(subtotal_cents * FLAT_VIP_RATE)
