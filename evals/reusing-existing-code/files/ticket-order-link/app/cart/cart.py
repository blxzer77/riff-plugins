"""Shopping carts."""

from app import db
from app.catalog.pricing import gross_cents
from app.catalog.products import get_product
from app.shipping.rates import shipping_cents


def new_cart(customer_id: int) -> dict:
    cart = {"id": db.next_id("carts"), "customer_id": customer_id, "lines": {}}
    db.CARTS[cart["id"]] = cart
    return cart


def add_item(cart_id: int, sku: str, qty: int = 1) -> dict:
    product = get_product(sku)
    if not product.active:
        raise ValueError(f"{sku} is no longer sold")
    if qty <= 0:
        raise ValueError("quantity must be positive")
    cart = db.CARTS[cart_id]
    cart["lines"][sku] = cart["lines"].get(sku, 0) + qty
    return cart


def remove_item(cart_id: int, sku: str) -> dict:
    cart = db.CARTS[cart_id]
    cart["lines"].pop(sku, None)
    return cart


def totals(cart_id: int, country: str) -> dict:
    lines = db.CARTS[cart_id]["lines"]
    subtotal = sum(gross_cents(get_product(sku), country) * qty for sku, qty in lines.items())
    weight = sum(get_product(sku).weight_grams * qty for sku, qty in lines.items())
    shipping = shipping_cents(country, weight, subtotal)
    return {"subtotal_cents": subtotal, "shipping_cents": shipping, "total_cents": subtotal + shipping}
