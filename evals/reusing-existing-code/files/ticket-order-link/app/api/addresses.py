"""Address book endpoints."""

from app.addresses import book
from app.api.responses import error, ok

REQUIRED = ("name", "street", "postcode", "city")


def post_address(payload: dict, customer_id: int):
    missing = [field for field in REQUIRED if not payload.get(field)]
    if missing:
        return error(422, f"missing: {', '.join(missing)}")
    try:
        address = book.add_address(customer_id, *(payload[field] for field in REQUIRED),
                                   country=payload.get("country", "DE"))
    except ValueError as exc:
        return error(422, str(exc))
    return ok(address, status=201)


def get_addresses(payload: dict, customer_id: int):
    return ok(book.list_addresses(customer_id))


def delete_address(payload: dict, customer_id: int):
    try:
        address = book.get_address(int(payload["id"]))
    except (KeyError, ValueError, LookupError):
        return error(404, "no such address")
    if address["customer_id"] != customer_id:
        return error(404, "no such address")
    book.remove_address(address["id"])
    return ok(None, status=204)
