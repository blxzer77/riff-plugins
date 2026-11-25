"""Order numbers customers see."""

from app import db

PREFIX = "A-"
FIRST = 1001


def next_order_number() -> str:
    return f"{PREFIX}{FIRST + db.next_id('order_numbers') - 1}"
