"""Message texts."""

TEMPLATES = {
    "order_shipped_email": (
        "Your order {number} is on its way",
        "Hello {name},\n\nyour order {number} has shipped. Track it here: {url}\n\nLumen Leuchten",
    ),
    "order_shipped_sms": (None, "Lumen: order {number} has shipped. Tracking: {url}"),
    "password_reset_email": ("Reset your password", "Hello {name},\n\nreset your password here: {url}\n"),
    "login_code_sms": (None, "Your Lumen login code is {code}. It expires in 10 minutes."),
}


def render(template: str, **context) -> tuple[str | None, str]:
    subject, body = TEMPLATES[template]
    return (subject.format(**context) if subject else None), body.format(**context)
