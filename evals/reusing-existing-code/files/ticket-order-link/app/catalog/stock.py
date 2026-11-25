"""Stock levels, reserved when an order is placed."""

STOCK = {"LMN-1001": 12, "LMN-1002": 3, "LMN-2001": 25, "LMN-3001": 4,
         "LMN-4001": 300, "LMN-4002": 180, "LMN-9001": 0}
_START = dict(STOCK)


def available(sku: str) -> int:
    return STOCK.get(sku, 0)


def reserve(sku: str, qty: int) -> None:
    if qty <= 0:
        raise ValueError("quantity must be positive")
    if available(sku) < qty:
        raise ValueError(f"only {available(sku)} of {sku} in stock")
    STOCK[sku] -= qty


def release(sku: str, qty: int) -> None:
    STOCK[sku] = available(sku) + qty


def reset() -> None:
    STOCK.clear()
    STOCK.update(_START)
