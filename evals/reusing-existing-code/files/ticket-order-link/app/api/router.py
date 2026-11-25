"""Routes of the JSON API. The web server calls dispatch() for every request."""

from app.accounts.sessions import current_customer
from app.api import accounts, addresses, orders
from app.api.responses import error

PUBLIC = {("POST", "/signup"): accounts.post_signup}
PRIVATE = {
    ("PUT", "/me/mobile"): accounts.put_mobile,
    ("POST", "/me/addresses"): addresses.post_address,
    ("GET", "/me/addresses"): addresses.get_addresses,
    ("DELETE", "/me/addresses"): addresses.delete_address,
    ("POST", "/checkout"): orders.post_checkout,
    ("GET", "/orders"): orders.get_order_status,
}


def dispatch(method: str, path: str, payload: dict | None = None, token: str | None = None):
    key = (method.upper(), path)
    payload = payload or {}
    if key in PUBLIC:
        return PUBLIC[key](payload)
    if key not in PRIVATE:
        return error(404, f"no route for {method} {path}")
    customer = current_customer(token) if token else None
    if customer is None:
        return error(401, "log in first")
    return PRIVATE[key](payload, customer["id"])
