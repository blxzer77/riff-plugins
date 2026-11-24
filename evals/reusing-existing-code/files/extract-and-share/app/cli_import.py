import csv
import io
import re
from datetime import date
from pathlib import Path

from app.store import ORDERS_DB

_SKU_RE = re.compile(r"^[A-Z]{2,4}-\d{4}$")
_REQUIRED_COLUMNS = {"order_id", "sku", "qty", "unit_price", "ordered_on"}


def run_cli(csv_path: str) -> int:
    text = Path(csv_path).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not _REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        print("ERROR: missing required CSV columns")
        return 2

    imported = 0
    errors: list[str] = []
    seen_ids: set[str] = set()
    for line_no, row in enumerate(reader, start=2):
        order_id = (row.get("order_id") or "").strip()
        sku = (row.get("sku") or "").strip().upper()
        if not order_id or order_id in seen_ids or order_id in ORDERS_DB:
            errors.append(f"line {line_no}: duplicate or empty order_id {order_id!r}")
            continue
        if not _SKU_RE.match(sku):
            errors.append(f"line {line_no}: invalid sku {sku!r}")
            continue
        try:
            qty = int((row.get("qty") or "").strip())
            cents = round(float((row.get("unit_price") or "").strip()) * 100)
            ordered_on = date.fromisoformat((row.get("ordered_on") or "").strip())
        except ValueError:
            errors.append(f"line {line_no}: invalid numeric or date field")
            continue
        if qty <= 0 or cents <= 0:
            errors.append(f"line {line_no}: qty and unit_price must be positive")
            continue
        seen_ids.add(order_id)
        ORDERS_DB[order_id] = {
            "order_id": order_id,
            "sku": sku,
            "qty": qty,
            "total_cents": qty * cents,
            "ordered_on": ordered_on.isoformat(),
        }
        imported += 1

    print(f"imported={imported} errors={len(errors)}")
    return 1 if errors and imported == 0 else 0
