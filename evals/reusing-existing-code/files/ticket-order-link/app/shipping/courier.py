"""Shipping labels for the courier's label API."""

from app.addresses.book import get_address
from app.shipping.parcels import parcel_weight_grams

SENDER = {"name": "Lumen Leuchten GmbH", "street": "Am Lichthof 3", "postcode": "50667",
          "city": "Köln", "country": "DE"}
SERVICE = "PARCEL"


def build_label(order: dict) -> dict:
    """The payload the courier's label endpoint takes for one parcel."""
    address = get_address(order["address_id"])
    return {
        "reference": order["number"],
        "service": SERVICE,
        "sender": SENDER,
        "recipient_name": address["name"],
        "recipient_street": address["street"],
        "recipient_postcode": address["postcode"],
        "recipient_city": address["city"],
        "recipient_country": address["country"],
        "weight_grams": parcel_weight_grams(order["lines"]),
    }
