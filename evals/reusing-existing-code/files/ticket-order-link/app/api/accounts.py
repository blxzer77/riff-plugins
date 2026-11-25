"""Account endpoints."""

from app.accounts import profile, signup
from app.api.responses import error, ok


def post_signup(payload: dict):
    try:
        customer = signup.create_customer(payload.get("email", ""), payload.get("password", ""),
                                          payload.get("name", ""))
    except ValueError as exc:
        return error(422, str(exc))
    return ok({"id": customer["id"], "email": customer["email"]}, status=201)


def put_mobile(payload: dict, customer_id: int):
    try:
        customer = profile.update_mobile(customer_id, payload.get("mobile", ""))
    except ValueError as exc:
        return error(422, str(exc))
    return ok({"mobile": customer["mobile"]})
