"""Parcel weights."""

from app.catalog.products import get_product

PACKAGING_GRAMS = 350


def parcel_weight_grams(lines: list[dict]) -> int:
    return PACKAGING_GRAMS + sum(get_product(l["sku"]).weight_grams * l["qty"] for l in lines)
