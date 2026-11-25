"""In-memory tables. Production swaps this module for the database layer."""

from itertools import count

CUSTOMERS: dict[int, dict] = {}
ADDRESSES: dict[int, dict] = {}
CARTS: dict[int, dict] = {}
ORDERS: dict[int, dict] = {}
PAYMENTS: dict[int, dict] = {}
REFUNDS: dict[int, dict] = {}
TICKETS: dict[int, dict] = {}
SESSIONS: dict[str, int] = {}

_TABLES = (CUSTOMERS, ADDRESSES, CARTS, ORDERS, PAYMENTS, REFUNDS, TICKETS, SESSIONS)
_sequences: dict[str, count] = {}


def next_id(sequence: str) -> int:
    return next(_sequences.setdefault(sequence, count(1)))


def reset() -> None:
    """Empty every table and restart the sequences."""
    for table in _TABLES:
        table.clear()
    _sequences.clear()
