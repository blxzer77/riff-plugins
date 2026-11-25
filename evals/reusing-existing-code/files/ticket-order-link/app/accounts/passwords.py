"""Password hashing and the password policy."""

import hashlib
import hmac
import os

ITERATIONS = 50_000
MIN_LENGTH = 10


def check_policy(password: str) -> None:
    if len(password) < MIN_LENGTH:
        raise ValueError(f"password must have at least {MIN_LENGTH} characters")
    if password.isdigit():
        raise ValueError("password must not be only digits")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, iterations, salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(candidate.hex(), digest)
