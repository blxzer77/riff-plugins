class PaymentDeclinedError(Exception):
    pass


def process_renewal(subscription: dict, charge_fn) -> dict:
    try:
        charge_fn(subscription["subscription_id"], subscription["amount"])
    except PaymentDeclinedError:
        subscription["status"] = "past_due"
        return {
            "subscription_id": subscription["subscription_id"],
            "status": "past_due",
        }
    subscription["status"] = "active"
    return {
        "subscription_id": subscription["subscription_id"],
        "status": "active",
    }
