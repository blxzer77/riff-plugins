"""Creating customer accounts."""

from app import db
from app.accounts.emails import normalize_email
from app.accounts.passwords import check_policy, hash_password


def create_customer(email: str, password: str, name: str) -> dict:
    email = normalize_email(email)
    if any(c["email"] == email for c in db.CUSTOMERS.values()):
        raise ValueError(f"an account with {email} already exists")
    check_policy(password)
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    customer = {
        "id": db.next_id("customers"),
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "mobile": None,
        "sms_updates": False,
        "marketing_opt_in": False,
    }
    db.CUSTOMERS[customer["id"]] = customer
    return customer
