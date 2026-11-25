"""Email addresses as customers type them."""

import re

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}")


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    if not _EMAIL.fullmatch(email):
        raise ValueError(f"not an email address: {raw!r}")
    return email
