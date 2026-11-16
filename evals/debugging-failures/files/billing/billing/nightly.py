import logging

from .charge import charge_with_retry
from .gateway import Gateway, GatewayError

log = logging.getLogger("billing")


def run(gateway, due):
    """Charge every (customer_id, amount_cents) in due. Declines are logged, not fatal."""
    results = {}
    for customer_id, amount in due:
        try:
            results[customer_id] = charge_with_retry(gateway, customer_id, amount)
        except GatewayError as e:
            if e.transient:
                raise
            log.warning("charge failed for %s: %s", customer_id, e.code)
            results[customer_id] = None
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(Gateway(), [])
