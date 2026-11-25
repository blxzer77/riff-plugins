"""Prices by destination country. Catalog prices include German VAT."""

from app import config
from app.catalog.products import Product


def net_cents(product: Product) -> int:
    return round(product.price_cents * 10_000 / (10_000 + config.VAT_BASIS_POINTS["DE"]))


def gross_cents(product: Product, country: str) -> int:
    if country == "DE":
        return product.price_cents
    return round(net_cents(product) * (10_000 + config.VAT_BASIS_POINTS[country]) / 10_000)


def format_eur(cents: int) -> str:
    euros, rest = divmod(abs(cents), 100)
    sign = "-" if cents < 0 else ""
    return f"{sign}{euros:,}".replace(",", ".") + f",{rest:02d} €"
