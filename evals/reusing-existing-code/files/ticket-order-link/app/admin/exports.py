"""CSV exports for the back office."""

import csv
import io

from app import db

CUSTOMER_COLUMNS = ("id", "email", "name", "mobile", "sms_updates", "marketing_opt_in")


def customers_csv() -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CUSTOMER_COLUMNS)
    for customer in sorted(db.CUSTOMERS.values(), key=lambda c: c["id"]):
        writer.writerow(["" if customer[c] is None else customer[c] for c in CUSTOMER_COLUMNS])
    return buffer.getvalue()
