"""Voucher codes."""

from datetime import date

VOUCHERS = {
    "WELCOME10": {"percent": 10, "min_subtotal_cents": 5000, "expires": date(2027, 3, 31)},
    "LIGHT5": {"amount_cents": 500, "min_subtotal_cents": 2500, "expires": date(2026, 12, 31)},
}


def discount_cents(code: str, subtotal_cents: int, today: date | None = None) -> int:
    voucher = VOUCHERS.get(code.strip().upper())
    if voucher is None:
        raise ValueError(f"unknown voucher {code!r}")
    if (today or date.today()) > voucher["expires"]:
        raise ValueError(f"voucher {code!r} has expired")
    if subtotal_cents < voucher["min_subtotal_cents"]:
        raise ValueError(f"voucher {code!r} needs a larger order")
    if "percent" in voucher:
        return subtotal_cents * voucher["percent"] // 100
    return min(voucher["amount_cents"], subtotal_cents)
