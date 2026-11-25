"""Outgoing messages. The delivery workers drain this list."""

OUTBOX: list[dict] = []


def record(channel: str, to: str, body: str, subject: str | None = None) -> dict:
    message = {"channel": channel, "to": to, "subject": subject, "body": body}
    OUTBOX.append(message)
    return message
