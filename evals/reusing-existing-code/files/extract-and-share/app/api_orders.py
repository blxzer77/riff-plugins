from app.store import ORDERS_DB


def list_orders() -> list[dict]:
    return list(ORDERS_DB.values())
