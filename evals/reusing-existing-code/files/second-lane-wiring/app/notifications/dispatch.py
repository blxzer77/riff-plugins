DISPATCH_LOG: list[dict] = []
OPTED_OUT_USERS: set[str] = set()

TEMPLATES: dict[str, tuple[str, str]] = {
    "invoice_paid": (
        "Invoice {invoice_id} paid",
        "Payment of {amount} received for invoice {invoice_id}.",
    ),
    "trial_ending": (
        "Trial ending soon",
        "Your trial for plan {plan} ends in {days} days.",
    ),
}


def send_notification(
    user_id: str,
    event: str,
    context: dict,
    *,
    channel: str = "email",
    critical: bool = False,
) -> dict | None:
    if event not in TEMPLATES:
        raise ValueError(f"unknown notification event: {event}")
    if not critical and user_id in OPTED_OUT_USERS:
        return None
    subject_tpl, body_tpl = TEMPLATES[event]
    entry = {
        "user_id": user_id,
        "event": event,
        "channel": channel,
        "subject": subject_tpl.format(**context),
        "body": body_tpl.format(**context),
    }
    DISPATCH_LOG.append(entry)
    return entry
