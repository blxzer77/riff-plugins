"""Search over the active catalog."""

from app.catalog.products import Product, list_active


def search(query: str) -> list[Product]:
    words = query.lower().split()
    return [p for p in list_active() if all(w in p.name.lower() for w in words)]
