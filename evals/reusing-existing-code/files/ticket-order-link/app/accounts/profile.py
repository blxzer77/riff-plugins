"""Changes customers make to their own account."""

from app import db
from app.notifications.sms import to_msisdn


def get_customer(customer_id: int) -> dict:
    try:
        return db.CUSTOMERS[customer_id]
    except KeyError:
        raise LookupError(f"no customer {customer_id}") from None


def rename(customer_id: int, name: str) -> dict:
    customer = get_customer(customer_id)
    if not name.strip():
        raise ValueError("name is required")
    customer["name"] = name.strip()
    return customer


def update_mobile(customer_id: int, raw: str) -> dict:
    """Set the mobile phone number used for login codes and shipping texts."""
    customer = get_customer(customer_id)
    customer["mobile"] = to_msisdn(raw)
    return customer


def remove_mobile(customer_id: int) -> dict:
    customer = get_customer(customer_id)
    customer["mobile"] = None
    customer["sms_updates"] = False
    return customer


def set_sms_updates(customer_id: int, enabled: bool) -> dict:
    customer = get_customer(customer_id)
    if enabled and not customer["mobile"]:
        raise ValueError("add a mobile number before turning on text updates")
    customer["sms_updates"] = enabled
    return customer


def set_marketing_opt_in(customer_id: int, opted_in: bool) -> dict:
    customer = get_customer(customer_id)
    customer["marketing_opt_in"] = opted_in
    return customer
