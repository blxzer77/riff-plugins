"""Order endpoints."""

from app.api.responses import error, ok
from app.checkout.checkout import place_order
from app.orders.service import get_order


def post_checkout(payload: dict, customer_id: int):
    try:
        order = place_order(int(payload["cart_id"]), int(payload["address_id"]),
                            payload.get("payment_method", "card"), payload.get("voucher"))
    except (KeyError, ValueError) as exc:
        return error(422, str(exc))
    except PermissionError as exc:
        return error(403, str(exc))
    return ok({"number": order["number"], "status": order["status"],
               "total_cents": order["total_cents"]}, status=201)


def get_order_status(payload: dict, customer_id: int):
    try:
        order = get_order(int(payload["id"]))
    except (KeyError, ValueError, LookupError):
        return error(404, "no such order")
    if order["customer_id"] != customer_id:
        return error(404, "no such order")
    return ok({"number": order["number"], "status": order["status"],
               "tracking_number": order["tracking_number"]})
