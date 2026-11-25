"""Email through the mail relay."""

from app.notifications.outbox import record


def send_email(to: str, subject: str, body: str) -> dict:
    return record("email", to, body, subject=subject)
