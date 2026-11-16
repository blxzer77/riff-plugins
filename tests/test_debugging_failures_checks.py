"""Validates the debugging-failures eval checks: the untouched fixtures fail, root-cause
fixes written in different ways pass, and symptom fixes fail."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals" / "debugging-failures"


def apply(workdir: Path, rel: str, old: str, new: str) -> None:
    path = workdir / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, (rel, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


CONTACTS_CSV = (
    "contacts/importer.py",
    'from dataclasses import dataclass\n',
    'import csv\nfrom dataclasses import dataclass\n',
), (
    "contacts/importer.py",
    '''def parse_line(line: str) -> Contact:
    name, email, company = line.rstrip("\\r\\n").split(",")
''',
    '''def parse_line(line: str) -> Contact:
    name, email, company = next(csv.reader([line]))
''',
)
CONTACTS_LATIN1 = ("contacts/importer.py", 'encoding="utf-8"', 'encoding="latin-1"'),
CONTACTS_SKIP = (
    "contacts/importer.py",
    '''        return [parse_line(line) for line in f if line.strip()]''',
    '''        out = []
        for line in f:
            try:
                out.append(parse_line(line))
            except ValueError:
                pass
        return out''',
),
CONTACTS_MAXSPLIT = ("contacts/importer.py", '.split(",")', '.split(",", 2)'),

BILLING_TRANSIENT = (
    "billing/charge.py",
    '''        except TimeoutError:
            if attempt == attempts - 1:''',
    '''        except (TimeoutError, GatewayError) as e:
            if isinstance(e, GatewayError) and not e.transient:
                raise
            if attempt == attempts - 1:''',
), ("billing/charge.py", "import uuid\n", "import uuid\n\nfrom .gateway import GatewayError\n")
BILLING_TRANSIENT_HELPER = (
    "billing/charge.py",
    '''        except TimeoutError:
            if attempt == attempts - 1:''',
    '''        except Exception as e:
            from .gateway import GatewayError
            retryable = isinstance(e, TimeoutError) or (isinstance(e, GatewayError) and e.transient)
            if not retryable or attempt == attempts - 1:''',
),
BILLING_WIDE_GATEWAY = (
    "billing/charge.py", "except TimeoutError:", "except (TimeoutError, GatewayError):",
), ("billing/charge.py", "import uuid\n", "import uuid\n\nfrom .gateway import GatewayError\n")
BILLING_EXCEPT_ALL = ("billing/charge.py", "except TimeoutError:", "except Exception:"),

REPORTS_NONE = (
    "reports/summary.py",
    '''def summarize(rows, totals={}):
    """Total amount per region for the given rows."""
''',
    '''def summarize(rows, totals=None):
    """Total amount per region for the given rows."""
    totals = {} if totals is None else totals
''',
),
REPORTS_NO_PARAM = (
    "reports/summary.py",
    '''def summarize(rows, totals={}):
    """Total amount per region for the given rows."""
''',
    '''def summarize(rows):
    """Total amount per region for the given rows."""
    totals = {}
''',
),
REPORTS_CALLER_ONLY = ("reports/__main__.py", "summarize(list(group))", "summarize(list(group), {})"),


class DebuggingFailuresChecks(unittest.TestCase):
    def run_check(self, fixture: str, check: str, edits=()) -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / fixture
            shutil.copytree(EVALS / "files" / fixture, work)
            for edit in edits:
                apply(work, *edit)
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work)},
                               capture_output=True, text=True, timeout=120)
            return r.returncode == 0

    def test_untouched_fixtures_fail(self):
        self.assertFalse(self.run_check("contacts", "contacts_fixed.py"))
        self.assertFalse(self.run_check("billing", "billing_retry_fixed.py"))
        self.assertFalse(self.run_check("reports", "reports_fixed.py"))

    def test_root_cause_fixes_pass(self):
        self.assertTrue(self.run_check("contacts", "contacts_fixed.py", CONTACTS_CSV))
        self.assertTrue(self.run_check("billing", "billing_retry_fixed.py", BILLING_TRANSIENT))
        self.assertTrue(self.run_check("billing", "billing_retry_fixed.py", BILLING_TRANSIENT_HELPER))
        self.assertTrue(self.run_check("reports", "reports_fixed.py", REPORTS_NONE))
        self.assertTrue(self.run_check("reports", "reports_fixed.py", REPORTS_NO_PARAM))

    def test_symptom_fixes_fail(self):
        for edits in (CONTACTS_LATIN1, CONTACTS_SKIP, CONTACTS_MAXSPLIT):
            self.assertFalse(self.run_check("contacts", "contacts_fixed.py", edits), edits)
        for edits in (BILLING_WIDE_GATEWAY, BILLING_EXCEPT_ALL):
            self.assertFalse(self.run_check("billing", "billing_retry_fixed.py", edits), edits)
        self.assertFalse(self.run_check("reports", "reports_fixed.py", REPORTS_CALLER_ONLY))


if __name__ == "__main__":
    unittest.main()
