import csv
import io

from app.models import Customer, Order, Refund


def export_orders_csv(orders: list[Order]) -> dict:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["order_id", "customer_id", "total", "placed_at"])
    total_cents = 0
    for order in orders:
        total_cents += order.total_cents
        writer.writerow([
            order.order_id,
            order.customer_id,
            f"{order.total_cents / 100:.2f}",
            order.placed_at.isoformat(),
        ])
    return {
        "filename": "orders.csv",
        "content": buf.getvalue(),
        "row_count": len(orders),
        "total_amount": f"{total_cents / 100:.2f}",
    }


def export_customers_csv(customers: list[Customer]) -> dict:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["customer_id", "email", "lifetime_spend", "joined_at"])
    total_cents = 0
    for customer in customers:
        total_cents += customer.lifetime_cents
        writer.writerow([
            customer.customer_id,
            customer.email,
            f"{customer.lifetime_cents / 100:.2f}",
            customer.joined_at.isoformat(),
        ])
    return {
        "filename": "customers.csv",
        "content": buf.getvalue(),
        "row_count": len(customers),
        "total_amount": f"{total_cents / 100:.2f}",
    }


def export_refunds_csv(refunds: list[Refund]) -> dict:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["refund_id", "order_id", "amount", "refunded_at"])
    total_cents = 0
    for refund in refunds:
        total_cents += refund.amount_cents
        writer.writerow([
            refund.refund_id,
            refund.order_id,
            f"{refund.amount_cents / 100:.2f}",
            refund.refunded_at.isoformat(),
        ])
    return {
        "filename": "refunds.csv",
        "content": buf.getvalue(),
        "row_count": len(refunds),
        "total_amount": f"{total_cents / 100:.2f}",
    }
