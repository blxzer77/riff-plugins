"""Validates the reusing-existing-code eval checks: untouched fixtures fail, two correct
solutions written differently pass, copy-paste near-misses and rewrites of an existing
rule fail, and shared code moved into a new grab-bag module fails the shared-module check."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "reusing-existing-code"

UNTOUCHED, GOOD, ALT, ALT2, MISS, MISS2, MISS3, GRAB_BAG = (
    "untouched", "good", "alternative", "alternative-2", "near-miss", "near-miss-2", "near-miss-3",
    "grab-bag")

# Files that replace or add to the fixture, per variant.

SYNONYM = {
    GOOD: {"app/api/members.py": '''from app.core.identity import canonicalize_account_slug

MEMBERS: dict[str, dict] = {}


def list_members() -> list[dict]:
    return list(MEMBERS.values())


def register_member(display_handle: str, email: str) -> dict:
    username = canonicalize_account_slug(display_handle, max_length=32)
    member = {"username": username, "email": email.strip().lower()}
    MEMBERS[username] = member
    return member
'''},
    ALT: {"app/core/identity.py": None,  # keep, then append below
          "app/api/members.py": '''from app.core import identity

MEMBERS: dict[str, dict] = {}


def list_members() -> list[dict]:
    return list(MEMBERS.values())


def register_member(display_handle: str, email: str) -> dict:
    handle = identity.canonicalize_username(display_handle)
    MEMBERS[handle] = {"handle": handle, "email": email}
    return MEMBERS[handle]
'''},
    MISS: {"app/api/members.py": '''import re
import unicodedata

MEMBERS: dict[str, dict] = {}


def list_members() -> list[dict]:
    return list(MEMBERS.values())


def _username(raw: str) -> str:
    text = unicodedata.normalize("NFKD", raw.strip()).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:32].rstrip("-")
    if len(name) < 3:
        raise ValueError(raw)
    return name


def register_member(display_handle: str, email: str) -> dict:
    username = _username(display_handle)
    MEMBERS[username] = {"username": username, "email": email}
    return MEMBERS[username]
'''},
}
SYNONYM_APPEND = {ALT: ("app/core/identity.py", '''

def canonicalize_username(raw: str) -> str:
    return canonicalize_account_slug(raw, max_length=32)
''')}

EXPORTERS_GOOD = '''import csv
import io

from app.models import Customer, Invoice, Order, Refund


def _export_csv(filename, header, records, row, cents):
    buf = io.StringIO()
    buf.write("\\ufeff")
    writer = csv.writer(buf, lineterminator="\\n")
    writer.writerow(header)
    total_cents = 0
    for record in records:
        total_cents += cents(record)
        writer.writerow(row(record))
    return {
        "filename": filename,
        "content": buf.getvalue(),
        "row_count": len(records),
        "total_amount": f"{total_cents / 100:.2f}",
    }


def _money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def export_orders_csv(orders: list[Order]) -> dict:
    return _export_csv("orders.csv", ["order_id", "customer_id", "total", "placed_at"], orders,
                       lambda o: [o.order_id, o.customer_id, _money(o.total_cents), o.placed_at.isoformat()],
                       lambda o: o.total_cents)


def export_customers_csv(customers: list[Customer]) -> dict:
    return _export_csv("customers.csv", ["customer_id", "email", "lifetime_spend", "joined_at"], customers,
                       lambda c: [c.customer_id, c.email, _money(c.lifetime_cents), c.joined_at.isoformat()],
                       lambda c: c.lifetime_cents)


def export_refunds_csv(refunds: list[Refund]) -> dict:
    return _export_csv("refunds.csv", ["refund_id", "order_id", "amount", "refunded_at"], refunds,
                       lambda r: [r.refund_id, r.order_id, _money(r.amount_cents), r.refunded_at.isoformat()],
                       lambda r: r.amount_cents)


def export_invoices_csv(invoices: list[Invoice]) -> dict:
    return _export_csv("invoices.csv", ["invoice_id", "customer_id", "amount", "issued_at"], invoices,
                       lambda i: [i.invoice_id, i.customer_id, _money(i.amount_cents), i.issued_at.isoformat()],
                       lambda i: i.amount_cents)
'''

EXPORTERS_ALT = '''import csv
import io
from dataclasses import dataclass

from app.models import Invoice


@dataclass(frozen=True)
class Column:
    name: str
    attr: str
    money: bool = False


ORDERS = ("orders.csv", "total_cents", [Column("order_id", "order_id"), Column("customer_id", "customer_id"),
                                         Column("total", "total_cents", True), Column("placed_at", "placed_at")])
CUSTOMERS = ("customers.csv", "lifetime_cents", [Column("customer_id", "customer_id"), Column("email", "email"),
                                                  Column("lifetime_spend", "lifetime_cents", True),
                                                  Column("joined_at", "joined_at")])
REFUNDS = ("refunds.csv", "amount_cents", [Column("refund_id", "refund_id"), Column("order_id", "order_id"),
                                           Column("amount", "amount_cents", True), Column("refunded_at", "refunded_at")])
INVOICES = ("invoices.csv", "amount_cents", [Column("invoice_id", "invoice_id"), Column("customer_id", "customer_id"),
                                             Column("amount", "amount_cents", True), Column("issued_at", "issued_at")])


def _cell(record, column):
    value = getattr(record, column.attr)
    if column.money:
        return f"{value / 100:.2f}"
    return value.isoformat() if hasattr(value, "isoformat") else value


def export(spec, records) -> dict:
    filename, amount_attr, columns = spec
    out = io.StringIO()
    out.write("\\ufeff")
    w = csv.DictWriter(out, fieldnames=[c.name for c in columns], lineterminator="\\n")
    w.writeheader()
    for r in records:
        w.writerow({c.name: _cell(r, c) for c in columns})
    total = sum(getattr(r, amount_attr) for r in records)
    return {"filename": filename, "content": out.getvalue(), "row_count": len(records),
            "total_amount": f"{total / 100:.2f}"}


def export_orders_csv(orders):
    return export(ORDERS, orders)


def export_customers_csv(customers):
    return export(CUSTOMERS, customers)


def export_refunds_csv(refunds):
    return export(REFUNDS, refunds)


def export_invoices_csv(invoices: list[Invoice]):
    return export(INVOICES, invoices)
'''

FOURTH_COPY = '''


def export_invoices_csv(invoices) -> dict:
    buf = io.StringIO()
    buf.write("\\ufeff")
    writer = csv.writer(buf, lineterminator="\\n")
    writer.writerow(["invoice_id", "customer_id", "amount", "issued_at"])
    total_cents = 0
    for invoice in invoices:
        total_cents += invoice.amount_cents
        writer.writerow([
            invoice.invoice_id,
            invoice.customer_id,
            f"{invoice.amount_cents / 100:.2f}",
            invoice.issued_at.isoformat(),
        ])
    return {
        "filename": "invoices.csv",
        "content": buf.getvalue(),
        "row_count": len(invoices),
        "total_amount": f"{total_cents / 100:.2f}",
    }
'''

FOURTH = {GOOD: {"app/exporters.py": EXPORTERS_GOOD}, ALT: {"app/exporters.py": EXPORTERS_ALT}}
FOURTH_APPEND = {MISS: ("app/exporters.py", FOURTH_COPY)}

ORDER_RULES = '''import csv
import io
import re
from datetime import date

from app.store import ORDERS_DB

SKU_RE = re.compile(r"^[A-Z]{2,4}-\\d{4}$")
REQUIRED_COLUMNS = {"order_id", "sku", "qty", "unit_price", "ordered_on"}


class MissingColumnsError(ValueError):
    pass


def import_rows(text: str) -> tuple[int, list[str]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise MissingColumnsError("missing required CSV columns")
    imported = 0
    errors: list[str] = []
    seen_ids: set[str] = set()
    for line_no, row in enumerate(reader, start=2):
        order_id = (row.get("order_id") or "").strip()
        sku = (row.get("sku") or "").strip().upper()
        if not order_id or order_id in seen_ids or order_id in ORDERS_DB:
            errors.append(f"line {line_no}: duplicate or empty order_id {order_id!r}")
            continue
        if not SKU_RE.match(sku):
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
        ORDERS_DB[order_id] = {"order_id": order_id, "sku": sku, "qty": qty,
                               "total_cents": qty * cents, "ordered_on": ordered_on.isoformat()}
        imported += 1
    return imported, errors
'''

CLI_GOOD = '''from pathlib import Path

from app.order_rules import MissingColumnsError, import_rows


def run_cli(csv_path: str) -> int:
    text = Path(csv_path).read_text(encoding="utf-8")
    try:
        imported, errors = import_rows(text)
    except MissingColumnsError:
        print("ERROR: missing required CSV columns")
        return 2
    print(f"imported={imported} errors={len(errors)}")
    return 1 if errors and imported == 0 else 0
'''

API_GOOD = '''from app.order_rules import import_rows
from app.store import ORDERS_DB


def list_orders() -> list[dict]:
    return list(ORDERS_DB.values())


def import_orders_payload(csv_text: str) -> dict:
    imported, errors = import_rows(csv_text)
    return {"imported": imported, "errors": errors}
'''

# Alternative: per-row rules shared, each importer keeps its own short loop that calls them.
CLI_ALT = '''import csv
import io
import re
from datetime import date
from pathlib import Path

from app.store import ORDERS_DB

_SKU_RE = re.compile(r"^[A-Z]{2,4}-\\d{4}$")
REQUIRED_COLUMNS = {"order_id", "sku", "qty", "unit_price", "ordered_on"}


def build_order(row: dict, seen_ids: set[str]) -> tuple[dict | None, str | None]:
    order_id = (row.get("order_id") or "").strip()
    sku = (row.get("sku") or "").strip().upper()
    if not order_id or order_id in seen_ids or order_id in ORDERS_DB:
        return None, f"duplicate or empty order_id {order_id!r}"
    if not _SKU_RE.match(sku):
        return None, f"invalid sku {sku!r}"
    try:
        qty = int((row.get("qty") or "").strip())
        cents = round(float((row.get("unit_price") or "").strip()) * 100)
        ordered_on = date.fromisoformat((row.get("ordered_on") or "").strip())
    except ValueError:
        return None, "invalid numeric or date field"
    if qty <= 0 or cents <= 0:
        return None, "qty and unit_price must be positive"
    return {"order_id": order_id, "sku": sku, "qty": qty, "total_cents": qty * cents,
            "ordered_on": ordered_on.isoformat()}, None


def run_cli(csv_path: str) -> int:
    text = Path(csv_path).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        print("ERROR: missing required CSV columns")
        return 2
    imported, errors, seen = 0, [], set()
    for line_no, row in enumerate(reader, start=2):
        order, error = build_order(row, seen)
        if error:
            errors.append(f"line {line_no}: {error}")
            continue
        seen.add(order["order_id"])
        ORDERS_DB[order["order_id"]] = order
        imported += 1
    print(f"imported={imported} errors={len(errors)}")
    return 1 if errors and imported == 0 else 0
'''

API_ALT = '''import csv
import io

from app.cli_import import REQUIRED_COLUMNS, build_order
from app.store import ORDERS_DB


def list_orders() -> list[dict]:
    return list(ORDERS_DB.values())


def import_orders_payload(csv_text: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        raise ValueError("missing required CSV columns")
    imported, errors, seen = 0, [], set()
    for line_no, row in enumerate(reader, start=2):
        order, error = build_order(row, seen)
        if error:
            errors.append(f"line {line_no}: {error}")
            continue
        seen.add(order["order_id"])
        ORDERS_DB[order["order_id"]] = order
        imported += 1
    return {"imported": imported, "errors": errors}
'''

API_COPY = '''import csv
import io
import re
from datetime import date

from app.store import ORDERS_DB

SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\\d{4}$")


def list_orders() -> list[dict]:
    return list(ORDERS_DB.values())


def import_orders_payload(csv_text: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"order_id", "sku", "qty", "unit_price", "ordered_on"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("missing required columns")
    imported, errors, seen = 0, [], set()
    for line_no, row in enumerate(reader, start=2):
        order_id = (row.get("order_id") or "").strip()
        sku = (row.get("sku") or "").strip().upper()
        if not order_id or order_id in seen or order_id in ORDERS_DB:
            errors.append(f"line {line_no}: duplicate or empty order_id")
            continue
        if not SKU_PATTERN.match(sku):
            errors.append(f"line {line_no}: invalid sku")
            continue
        try:
            qty = int(row["qty"])
            cents = round(float(row["unit_price"]) * 100)
            ordered_on = date.fromisoformat(row["ordered_on"].strip())
        except (ValueError, TypeError):
            errors.append(f"line {line_no}: invalid field")
            continue
        if qty <= 0 or cents <= 0:
            errors.append(f"line {line_no}: qty and unit_price must be positive")
            continue
        seen.add(order_id)
        ORDERS_DB[order_id] = {"order_id": order_id, "sku": sku, "qty": qty,
                               "total_cents": qty * cents, "ordered_on": ordered_on.isoformat()}
        imported += 1
    return {"imported": imported, "errors": errors}
'''

# Half reuse: field rules shared, but each importer has its own duplicate-ID check.
API_HALF = '''import csv
import io

from app.order_fields import parse_fields
from app.store import ORDERS_DB

REQUIRED = {"order_id", "sku", "qty", "unit_price", "ordered_on"}


def list_orders() -> list[dict]:
    return list(ORDERS_DB.values())


def import_orders_payload(csv_text: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError("missing required columns")
    imported, errors, seen = 0, [], set()
    for line_no, row in enumerate(reader, start=2):
        order_id = (row.get("order_id") or "").strip()
        if not order_id or order_id in seen or order_id in ORDERS_DB:
            errors.append(f"line {line_no}: duplicate or empty order_id {order_id!r}")
            continue
        fields, error = parse_fields(row)
        if error:
            errors.append(f"line {line_no}: {error}")
            continue
        seen.add(order_id)
        ORDERS_DB[order_id] = {"order_id": order_id, **fields}
        imported += 1
    return {"imported": imported, "errors": errors}
'''

ORDER_FIELDS = '''import re
from datetime import date

SKU_RE = re.compile(r"^[A-Z]{2,4}-\\d{4}$")


def parse_fields(row: dict) -> tuple[dict | None, str | None]:
    sku = (row.get("sku") or "").strip().upper()
    if not SKU_RE.match(sku):
        return None, f"invalid sku {sku!r}"
    try:
        qty = int((row.get("qty") or "").strip())
        cents = round(float((row.get("unit_price") or "").strip()) * 100)
        ordered_on = date.fromisoformat((row.get("ordered_on") or "").strip())
    except ValueError:
        return None, "invalid numeric or date field"
    if qty <= 0 or cents <= 0:
        return None, "qty and unit_price must be positive"
    return {"sku": sku, "qty": qty, "total_cents": qty * cents, "ordered_on": ordered_on.isoformat()}, None
'''

CLI_HALF = '''import csv
import io
from pathlib import Path

from app.order_fields import parse_fields
from app.store import ORDERS_DB

_REQUIRED_COLUMNS = {"order_id", "sku", "qty", "unit_price", "ordered_on"}


def run_cli(csv_path: str) -> int:
    text = Path(csv_path).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not _REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        print("ERROR: missing required CSV columns")
        return 2
    imported, errors, seen_ids = 0, [], set()
    for line_no, row in enumerate(reader, start=2):
        order_id = (row.get("order_id") or "").strip()
        if not order_id or order_id in seen_ids or order_id in ORDERS_DB:
            errors.append(f"line {line_no}: duplicate or empty order_id {order_id!r}")
            continue
        fields, error = parse_fields(row)
        if error:
            errors.append(f"line {line_no}: {error}")
            continue
        seen_ids.add(order_id)
        ORDERS_DB[order_id] = {"order_id": order_id, **fields}
        imported += 1
    print(f"imported={imported} errors={len(errors)}")
    return 1 if errors and imported == 0 else 0
'''

SHARE = {GOOD: {"app/order_rules.py": ORDER_RULES, "app/cli_import.py": CLI_GOOD, "app/api_orders.py": API_GOOD},
         ALT: {"app/cli_import.py": CLI_ALT, "app/api_orders.py": API_ALT},
         MISS: {"app/api_orders.py": API_COPY},
         MISS2: {"app/order_fields.py": ORDER_FIELDS, "app/cli_import.py": CLI_HALF, "app/api_orders.py": API_HALF}}

# The good solutions with the shared code moved into a new grab-bag module.
_HEAD, _TAIL = EXPORTERS_GOOD.split("\n\n\ndef export_orders_csv", 1)
FOURTH[GRAB_BAG] = {
    "app/utils.py": _HEAD.replace("from app.models import Customer, Invoice, Order, Refund\n", ""),
    "app/exporters.py": ("from app.models import Customer, Invoice, Order, Refund\n"
                         "from app.utils import _export_csv, _money\n\n\ndef export_orders_csv" + _TAIL),
}
SHARE[GRAB_BAG] = {"app/common.py": ORDER_RULES,
                   "app/cli_import.py": CLI_GOOD.replace("app.order_rules", "app.common"),
                   "app/api_orders.py": API_GOOD.replace("app.order_rules", "app.common")}


# ticket-order-link: variants are edits of the fixture's own files.
def _fixture_text(rel: str) -> str:
    return (EVALS / "files" / "ticket-order-link" / rel).read_text(encoding="utf-8")


def _swap(text: str, old: str, new: str) -> str:
    assert old in text, f"fixture changed: {old!r} not found"
    return text.replace(old, new, 1)


TICKETS, TRANSFERS, NUMBERS = (_fixture_text(rel) for rel in (
    "app/support/tickets.py", "app/payments/transfers.py", "app/orders/numbers.py"))


def tickets_with(imports: str, find_order: str, helpers: str = "") -> str:
    """tickets.py whose open_ticket links the order id that `find_order` (a body) returns."""
    text = _swap(TICKETS, "from app import db\n", imports + "from app import db\n")
    text = _swap(text, '        raise ValueError("subject and message are required")\n',
                 '        raise ValueError("subject and message are required")\n'
                 '    if order_id is None:\n'
                 '        order_id = _mentioned_order(customer_id, subject, body)\n')
    return (text + helpers + "\n\ndef _mentioned_order(customer_id: int, subject: str, body: str)"
            " -> int | None:\n" + find_order)


OWN_ORDER = """    reference = {reader}(f"{{subject}}\\n{{body}}")
    for order in db.ORDERS.values():
        if order["number"] == reference and order["customer_id"] == customer_id:
            return order["id"]
    return None
"""
SPLIT_LOOKUP = """    number = find_order_number(subject) or find_order_number(body)
    order = next((o for o in db.ORDERS.values() if o["number"] == number), None)
    return order["id"] if order is not None and order["customer_id"] == customer_id else None
"""
FIND_ORDER_NUMBER = """
_IN_TEXT = re.compile(r"(?<![A-Z0-9])A\\s*[-–—./]?\\s*(\\d{4,7})(?!\\d)")


def find_order_number(text: str) -> str | None:
    \"\"\"The first order number in free text, however the customer wrote it.\"\"\"
    match = _IN_TEXT.search(text.upper())
    return f"{PREFIX}{match.group(1)}" if match else None
"""
EVERY_ORDER_NUMBER = """
_IN_TEXT = re.compile(r"(?<![A-Z0-9])A\\s*[-–—./]?\\s*(\\d{4,7})(?!\\d)")


def order_numbers_in(text: str) -> list[str]:
    return [f"{PREFIX}{m.group(1)}" for m in _IN_TEXT.finditer(text.upper())]


def first_order_number(text: str) -> str | None:
    numbers = order_numbers_in(text)
    return numbers[0] if numbers else None
"""
EVERY_LOOKUP = """    for text in (subject, body):
        for number in order_numbers_in(text):
            order = next((o for o in db.ORDERS.values() if o["number"] == number), None)
            if order is not None and order["customer_id"] == customer_id:
                return order["id"]
    return None
"""
# transfers.py importing the reader from elsewhere instead of defining it.
_head, _rest = TRANSFERS.split("from app.orders.numbers import PREFIX\n", 1)
_tail = _rest.split("\n\ndef match_transfer", 1)[1]
TRANSFERS_ON = _head + "from MODULE import find_order_number as reference_in\n\n\ndef match_transfer" + _tail

# A rewrite from the prompt's examples: it misses the dot, slash and dash spellings.
REWRITE = r"""

_ORDER = re.compile(r"\bA-?\s*(\d{4,})\b", re.IGNORECASE)


def _order_number(text: str) -> str | None:
    match = _ORDER.search(text)
    return f"A-{match.group(1)}" if match else None
"""
# The existing reader copied verbatim: it behaves the same and is a second copy.
COPY = "\n\n" + TRANSFERS[TRANSFERS.index("_LETTERS = "):TRANSFERS.index("\n\ndef match_transfer")].replace(
    "def reference_in(", "def _reference_in(")

TICKET = {
    GOOD: {"app/support/tickets.py": tickets_with("from app.payments.transfers import reference_in\n",
                                                  OWN_ORDER.format(reader="reference_in"))},
    # The reader moved to the module that owns order numbers and renamed; transfers.py imports it.
    ALT: {"app/orders/numbers.py": _swap(NUMBERS, "from app import db\n", "import re\n\nfrom app import db\n")
          + FIND_ORDER_NUMBER,
          "app/payments/transfers.py": TRANSFERS_ON.replace("MODULE", "app.orders.numbers"),
          "app/support/tickets.py": tickets_with("from app.orders.numbers import find_order_number\n",
                                                 SPLIT_LOOKUP)},
    # The reader moved next to the number format and returns every match; a wrapper keeps
    # the first for transfers.
    ALT2: {"app/orders/numbers.py": _swap(NUMBERS, "from app import db\n", "import re\n\nfrom app import db\n")
           + EVERY_ORDER_NUMBER,
           "app/payments/transfers.py": TRANSFERS_ON.replace("MODULE", "app.orders.numbers").replace(
               "find_order_number as reference_in", "first_order_number as reference_in"),
           "app/support/tickets.py": tickets_with("from app.orders.numbers import order_numbers_in\n",
                                                  EVERY_LOOKUP)},
    MISS: {"app/support/tickets.py": tickets_with("import re\n\n", OWN_ORDER.format(reader="_order_number"),
                                                  REWRITE)},
    MISS2: {"app/support/tickets.py": tickets_with("import re\n\nfrom app.orders.numbers import PREFIX\n",
                                                   OWN_ORDER.format(reader="_reference_in"), COPY)},
    # Reads the number with the existing code, but links other customers' orders too.
    MISS3: {"app/support/tickets.py": tickets_with(
        "from app.payments.transfers import reference_in\n",
        OWN_ORDER.format(reader="reference_in").replace(' and order["customer_id"] == customer_id', ""))},
    GRAB_BAG: {"app/utils.py": "import re\n\nfrom app.orders.numbers import PREFIX\n" + FIND_ORDER_NUMBER,
               "app/payments/transfers.py": TRANSFERS_ON.replace("MODULE", "app.utils"),
               "app/support/tickets.py": tickets_with("from app.utils import find_order_number\n",
                                                      SPLIT_LOOKUP)},
}

P, F = True, False
# fixture: (checks, variants, appends, {variant: verdict per check})
CASES = {
    "synonym-helper": (
        ["synonym_behavior", "synonym_reuse"], SYNONYM, SYNONYM_APPEND,
        {UNTOUCHED: [F, F], GOOD: [P, P], ALT: [P, P], MISS: [P, F]}),
    "fourth-variant": (
        ["exporters_behavior", "exporters_once", "no_new_shared_module"], FOURTH, FOURTH_APPEND,
        {UNTOUCHED: [F, F, P], GOOD: [P, P, P], ALT: [P, P, P], MISS: [P, F, P],
         GRAB_BAG: [P, P, F]}),
    "extract-and-share": (
        ["import_behavior", "import_rules_once", "import_duplicate_check_once",
         "no_new_shared_module"], SHARE, {},
        {UNTOUCHED: [F, F, F, P], GOOD: [P, P, P, P], ALT: [P, P, P, P], MISS: [P, F, F, P],
         MISS2: [P, P, F, P], GRAB_BAG: [P, P, P, F]}),
    "ticket-order-link": (
        ["ticket_link_behavior", "ticket_link_once", "no_new_shared_module"], TICKET, {},
        {UNTOUCHED: [F, F, P], GOOD: [P, P, P], ALT: [P, P, P], ALT2: [P, P, P], MISS: [F, F, P],
         MISS2: [P, F, P], MISS3: [F, P, P], GRAB_BAG: [P, P, F]}),
}


def run_check(check: str, workdir: Path, fixture: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, EVAL_WORKDIR=str(workdir), EVAL_FIXTURE=str(fixture),
               PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, str(EVALS / "checks" / f"{check}.py")], env=env,
                          capture_output=True, text=True, timeout=120)


class ReuseChecks(unittest.TestCase):
    def test_verdicts(self):
        for case, (checks, variants, appends, expected) in CASES.items():
            fixture = EVALS / "files" / case
            for name, want in expected.items():
                with tempfile.TemporaryDirectory() as tmp:
                    work = Path(tmp) / case
                    shutil.copytree(fixture, work, ignore=shutil.ignore_patterns("__pycache__"))
                    for rel, text in variants.get(name, {}).items():
                        if text is not None:  # None keeps the fixture's file
                            (work / rel).parent.mkdir(parents=True, exist_ok=True)
                            (work / rel).write_text(text, encoding="utf-8")
                    if name in appends:
                        rel, text = appends[name]
                        with open(work / rel, "a", encoding="utf-8") as fh:
                            fh.write(text)
                    for check, should_pass in zip(checks, want):
                        with self.subTest(case=case, variant=name, check=check):
                            r = run_check(check, work, fixture)
                            self.assertEqual(r.returncode == 0, should_pass, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
