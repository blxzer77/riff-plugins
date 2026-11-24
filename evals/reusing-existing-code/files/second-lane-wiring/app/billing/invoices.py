from app.notifications.dispatch import send_notification


def mark_invoice_paid(invoice_id: str, user_id: str, amount: str) -> dict:
    send_notification(
        user_id,
        "invoice_paid",
        {"invoice_id": invoice_id, "amount": amount},
    )
    return {"invoice_id": invoice_id, "status": "paid"}
