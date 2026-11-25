"""Customers' saved delivery addresses."""

from app import db
from app.addresses.postcodes import check_postcode


def add_address(customer_id: int, name: str, street: str, postcode: str, city: str,
                country: str = "DE") -> dict:
    if customer_id not in db.CUSTOMERS:
        raise LookupError(f"no customer {customer_id}")
    name, street, city = name.strip(), street.strip(), city.strip()
    if not (name and street and city):
        raise ValueError("name, street and city are required")
    address = {
        "id": db.next_id("addresses"),
        "customer_id": customer_id,
        "name": name,
        "street": street,
        "postcode": check_postcode(country, postcode),
        "city": city,
        "country": country,
        "is_default": not list_addresses(customer_id),
    }
    db.ADDRESSES[address["id"]] = address
    return address


def get_address(address_id: int) -> dict:
    try:
        return db.ADDRESSES[address_id]
    except KeyError:
        raise LookupError(f"no address {address_id}") from None


def list_addresses(customer_id: int) -> list[dict]:
    return [a for a in db.ADDRESSES.values() if a["customer_id"] == customer_id]


def set_default(address_id: int) -> dict:
    address = get_address(address_id)
    for other in list_addresses(address["customer_id"]):
        other["is_default"] = other["id"] == address_id
    return address


def remove_address(address_id: int) -> None:
    address = get_address(address_id)
    del db.ADDRESSES[address_id]
    remaining = list_addresses(address["customer_id"])
    if address["is_default"] and remaining:
        remaining[0]["is_default"] = True
