IDLE_LIMIT_SECONDS = 15 * 60


def is_active(session: dict, now: float) -> bool:
    """A session stays valid while the user was seen within the idle limit."""
    return now - session["last_seen"] <= IDLE_LIMIT_SECONDS


def touch(session: dict, now: float) -> None:
    session["last_seen"] = now
