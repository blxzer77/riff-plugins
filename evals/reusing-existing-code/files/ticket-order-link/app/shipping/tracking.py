"""Tracking links and the courier's status webhook."""

TRACKING_URL = "https://track.courier.example/{number}"
STATUSES = {"PU": "picked_up", "IT": "in_transit", "OD": "out_for_delivery",
            "DL": "delivered", "RT": "returned"}


def tracking_url(tracking_number: str) -> str:
    return TRACKING_URL.format(number=tracking_number)


def parse_status_event(payload: dict) -> tuple[str, str]:
    """(tracking number, status) from one webhook event."""
    try:
        return payload["parcel"]["number"], STATUSES[payload["event"]["code"]]
    except KeyError as missing:
        raise ValueError(f"unexpected tracking event: missing or unknown {missing}") from None
