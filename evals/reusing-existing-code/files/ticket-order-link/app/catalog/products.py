"""The product catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int  # gross, German VAT included
    weight_grams: int
    active: bool = True


PRODUCTS = {p.sku: p for p in (
    Product("LMN-1001", "Pendant lamp Oslo, oak", 12900, 1800),
    Product("LMN-1002", "Pendant lamp Oslo, black", 12900, 1800),
    Product("LMN-2001", "Desk lamp Bergen", 7900, 1200),
    Product("LMN-3001", "Floor lamp Lund", 21900, 5400),
    Product("LMN-4001", "LED bulb E27 2700K", 690, 60),
    Product("LMN-4002", "LED bulb GU10 3000K", 590, 40),
    Product("LMN-9001", "Wall lamp Malmo", 9900, 900, active=False),
)}


def get_product(sku: str) -> Product:
    try:
        return PRODUCTS[sku]
    except KeyError:
        raise LookupError(f"no product {sku}") from None


def list_active() -> list[Product]:
    return [p for p in PRODUCTS.values() if p.active]
