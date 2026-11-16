"""Validates the measuring-performance eval checks on the untouched fixtures, a real
fix, and near misses (a faster but different output, a caller switched to an
order-losing dedupe, a tokenizer sped up by dropping normalization)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "measuring-performance"

EXPORT_INDEXED = '''import json


def export_orders(orders, customers):
    """One JSON object per line: order id, customer name and email, total."""
    by_id = {}
    for c in customers:
        by_id.setdefault(c["id"], c)
    lines = []
    for order in orders:
        customer = by_id[order["customer_id"]]
        lines.append(json.dumps({
            "order": order["id"],
            "customer": customer["name"],
            "email": customer["email"],
            "total": round(order["total"], 2),
        }, sort_keys=True))
    return "\\n".join(lines)
'''
EXPORT_JSON_ONLY = '''def export_orders(orders, customers):
    lines = []
    for order in orders:
        customer = next(c for c in customers if c["id"] == order["customer_id"])
        lines.append('{"customer": "%s", "email": "%s", "order": "%s", "total": %s}' % (
            customer["name"], customer["email"], order["id"], round(order["total"], 2)))
    return "\\n".join(lines)
'''
EXPORT_FAST_WRONG = EXPORT_INDEXED.replace("round(order[\"total\"], 2)", "int(order[\"total\"])")


class MeasuringPerformanceChecks(unittest.TestCase):
    def run_check(self, fixture: str, check: str, files=None) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / fixture
            shutil.copytree(EVALS / "files" / fixture, work)
            for rel, edit in (files or {}).items():
                path = work / rel
                path.write_text(edit(path.read_text(encoding="utf-8")) if callable(edit) else edit,
                                encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work)},
                               capture_output=True, text=True, timeout=600)
            return r.returncode == 0

    def test_export(self):
        self.assertFalse(self.run_check("orders-export", "export_faster_same_output.py"))
        self.assertTrue(self.run_check("orders-export", "export_faster_same_output.py",
                                       {"orders/export.py": EXPORT_INDEXED}))
        self.assertFalse(self.run_check("orders-export", "export_faster_same_output.py",
                                        {"orders/export.py": EXPORT_JSON_ONLY}))
        self.assertFalse(self.run_check("orders-export", "export_faster_same_output.py",
                                        {"orders/export.py": EXPORT_FAST_WRONG}))

    def test_dedupe(self):
        self.assertTrue(self.run_check("dedupe", "dedupe_order_kept.py"))
        self.assertTrue(self.run_check("dedupe", "dedupe_order_kept.py", {
            "textutil/dedupe.py": lambda s: s.replace(
                "    seen = set()\n    out = []\n    for item in items:\n        if item not in seen:\n"
                "            seen.add(item)\n            out.append(item)\n    return out",
                "    return list(dict.fromkeys(items))")}))
        self.assertFalse(self.run_check("dedupe", "dedupe_order_kept.py", {
            "textutil/tags.py": lambda s: s.replace("import dedupe\n", "import dedupe_fast as dedupe\n")}))

    def test_tokenizer(self):
        self.assertTrue(self.run_check("tokenizer", "tokenize_unchanged.py"))
        self.assertFalse(self.run_check("tokenizer", "tokenize_unchanged.py", {
            "tok/tokenize.py": lambda s: s.replace('unicodedata.normalize("NFKC", text)', "text")}))


if __name__ == "__main__":
    unittest.main()
