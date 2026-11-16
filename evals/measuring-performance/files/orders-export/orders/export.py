import json


def export_orders(orders, customers):
    """One JSON object per line: order id, customer name and email, total."""
    lines = []
    for order in orders:
        customer = next(c for c in customers if c["id"] == order["customer_id"])
        lines.append(json.dumps({
            "order": order["id"],
            "customer": customer["name"],
            "email": customer["email"],
            "total": round(order["total"], 2),
        }, sort_keys=True))
    return "\n".join(lines)
