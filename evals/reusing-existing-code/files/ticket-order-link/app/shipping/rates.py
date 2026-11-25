"""Shipping costs."""

from app import config

# (up to grams, price in cents) by destination, lightest band first
RATES = {
    "DE": [(2000, 490), (10000, 690), (31500, 1290)],
    "AT": [(2000, 990), (10000, 1490), (31500, 2490)],
    "CH": [(2000, 1890), (10000, 2490), (31500, 3990)],
}


def shipping_cents(country: str, weight_grams: int, subtotal_cents: int) -> int:
    if country not in RATES:
        raise ValueError(f"we do not ship to {country!r}")
    if country == "DE" and subtotal_cents >= config.FREE_SHIPPING_FROM_CENTS:
        return 0
    for up_to, cents in RATES[country]:
        if weight_grams <= up_to:
            return cents
    raise ValueError(f"parcel too heavy: {weight_grams} g")
