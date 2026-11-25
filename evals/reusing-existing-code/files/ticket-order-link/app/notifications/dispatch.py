"""Which messages go out when something happens to an order or an account."""

from app.accounts.profile import get_customer
from app.notifications.email import send_email
from app.notifications.sms import send_sms
from app.notifications.templates import render
from app.shipping.tracking import tracking_url


def order_shipped(order: dict) -> list[dict]:
    customer = get_customer(order["customer_id"])
    url = tracking_url(order["tracking_number"])
    subject, body = render("order_shipped_email", name=customer["name"], number=order["number"], url=url)
    sent = [send_email(customer["email"], subject, body)]
    if customer["mobile"] and customer["sms_updates"]:
        _, text = render("order_shipped_sms", number=order["number"], url=url)
        sent.append(send_sms(customer["mobile"], text))
    return sent


def login_code(customer: dict, code: str) -> dict:
    if not customer["mobile"]:
        raise ValueError("customer has no mobile number")
    _, text = render("login_code_sms", code=code)
    return send_sms(customer["mobile"], text)
