import time
import uuid


def charge_with_retry(gateway, customer_id, amount_cents, attempts=3, sleep=time.sleep):
    """Charge once, retrying when the gateway times out. Returns the charge id."""
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    key = str(uuid.uuid4())
    for attempt in range(attempts):
        try:
            return gateway.charge(customer_id, amount_cents, idempotency_key=key)
        except TimeoutError:
            if attempt == attempts - 1:
                raise
            sleep(2 ** attempt)
