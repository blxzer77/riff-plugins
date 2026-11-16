import secrets

from .settings import COOKIE_NAME, SESSION_TTL_MINUTES


def new_session(user_id: str, now: float) -> dict:
    """Session record plus the cookie the browser keeps."""
    return {
        "id": secrets.token_hex(16),
        "user_id": user_id,
        "last_seen": now,
        "cookie": {"name": COOKIE_NAME, "max_age": SESSION_TTL_MINUTES * 60},
    }
