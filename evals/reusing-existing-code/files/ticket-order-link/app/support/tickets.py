"""Customer support tickets."""

from datetime import datetime, timezone

from app import db
from app.notifications.email import send_email


def open_ticket(customer_id: int, subject: str, body: str, order_id: int | None = None) -> dict:
    if not subject.strip() or not body.strip():
        raise ValueError("subject and message are required")
    ticket = {"id": db.next_id("tickets"), "customer_id": customer_id, "order_id": order_id,
              "subject": subject.strip(), "messages": [("customer", body.strip())],
              "status": "open", "opened_at": datetime.now(timezone.utc)}
    db.TICKETS[ticket["id"]] = ticket
    return ticket


def reply(ticket_id: int, agent: str, body: str) -> dict:
    ticket = db.TICKETS[ticket_id]
    if ticket["status"] == "closed":
        raise ValueError("ticket is closed")
    ticket["messages"].append((agent, body.strip()))
    ticket["status"] = "waiting"
    customer = db.CUSTOMERS[ticket["customer_id"]]
    send_email(customer["email"], f"Re: {ticket['subject']}", body.strip())
    return ticket


def close(ticket_id: int) -> dict:
    ticket = db.TICKETS[ticket_id]
    ticket["status"] = "closed"
    return ticket
