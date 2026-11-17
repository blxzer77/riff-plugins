"""Apply order events. Amounts are in cents."""


class OrderError(Exception):
    """The event is not allowed in the order's current state."""


class Order:
    def __init__(self, total: int):
        self.total = total
        self.status = "new"  # new, paid, shipped, refunded, reopened, cancelled
        self.paid = 0
        self.refunded = 0
        self.shipped = False


def apply(order: Order, event: str, amount: int = 0) -> None:
    if event == "pay":
        if order.status not in ("new", "reopened"):
            raise OrderError(f"cannot pay a {order.status} order")
        order.paid = order.total
        order.status = "paid"
    elif event == "ship":
        if order.shipped:
            raise OrderError("already shipped")
        if order.paid < order.total:
            raise OrderError("not paid")
        order.shipped = True
        order.status = "shipped"
    elif event == "refund":
        if order.paid == 0:
            raise OrderError("nothing to refund")
        if amount <= 0:
            raise OrderError("refund must be positive")
        order.refunded += amount
        order.status = "refunded"
    elif event == "reopen":
        # Support reopens a refunded order when the customer wants it after all;
        # the customer then pays again.
        if order.status != "refunded" or order.shipped:
            raise OrderError("only an unshipped refunded order can be reopened")
        order.status = "reopened"
    elif event == "cancel":
        if order.status not in ("new", "reopened"):
            raise OrderError(f"cannot cancel a {order.status} order")
        order.status = "cancelled"
    else:
        raise OrderError(f"unknown event {event}")
