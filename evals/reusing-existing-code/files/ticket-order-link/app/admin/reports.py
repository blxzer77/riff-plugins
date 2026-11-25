"""Numbers for the weekly business review."""

from collections import Counter

from app import db

COUNTED = ("paid", "shipped")


def sales_summary() -> dict:
    orders = [o for o in db.ORDERS.values() if o["status"] in COUNTED]
    units = Counter()
    for order in orders:
        for line in order["lines"]:
            units[line["sku"]] += line["qty"]
    return {
        "orders": len(orders),
        "revenue_cents": sum(o["total_cents"] for o in orders),
        "refunded_cents": sum(r["amount_cents"] for r in db.REFUNDS.values()),
        "top_skus": [sku for sku, _ in units.most_common(3)],
    }
