"""Import bank statements exported as CSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = ["Date", "Description", "Amount", "Category"]


@dataclass
class ImportResult:
    transactions: list[dict] = field(default_factory=list)
    skipped: int = 0


def parse_statement(text: str) -> ImportResult:
    lines = text.split("\n")
    result = ImportResult()
    if not lines or lines[0].split(",") != COLUMNS:
        return result
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) != len(COLUMNS):
            result.skipped += 1
            continue
        raw_date, description, raw_amount, category = parts
        try:
            row = {"date": date.fromisoformat(raw_date), "description": description,
                   "amount": Decimal(raw_amount), "category": category}
        except (ValueError, InvalidOperation):
            result.skipped += 1
            continue
        result.transactions.append(row)
    return result


def import_statement(path: str | Path) -> ImportResult:
    with open(path, encoding="utf-8", newline="") as fh:
        return parse_statement(fh.read())
