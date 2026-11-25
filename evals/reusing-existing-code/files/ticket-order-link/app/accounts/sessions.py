"""Login sessions."""

import secrets

from app import db
from app.accounts.emails import normalize_email
from app.accounts.passwords import verify_password


def login(email: str, password: str) -> str:
    email = normalize_email(email)
    for customer in db.CUSTOMERS.values():
        if customer["email"] == email and verify_password(password, customer["password_hash"]):
            token = secrets.token_urlsafe(24)
            db.SESSIONS[token] = customer["id"]
            return token
    raise PermissionError("wrong email or password")


def current_customer(token: str) -> dict | None:
    customer_id = db.SESSIONS.get(token)
    return db.CUSTOMERS.get(customer_id) if customer_id else None


def logout(token: str) -> None:
    db.SESSIONS.pop(token, None)
