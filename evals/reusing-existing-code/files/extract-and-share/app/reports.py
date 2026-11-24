from app.store import ORDERS_DB


def total_revenue_cents() -> int:
    return sum(o["total_cents"] for o in ORDERS_DB.values())
