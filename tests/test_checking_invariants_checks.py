"""Validates the checking-invariants eval checks: the untouched fixture fails, a complete
fix passes, and partial fixes (no reorder support, overwritten payments) fail."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JAR = os.environ.get("TLA2TOOLS") or str(Path.home() / ".cache/riff-skills/tools/tla2tools-1.7.4.jar")
JAVA = shutil.which("java")
EVALS = REPO / "evals" / "checking-invariants"
WORKFLOW = EVALS / "files" / "orders-workflow" / "orders" / "workflow.py"

GOOD = {
    "        order.paid = order.total\n": "        order.paid += order.total\n",
    "        if order.paid < order.total:\n": "        if order.paid - order.refunded < order.total:\n",
    "        if amount <= 0:\n            raise OrderError(\"refund must be positive\")\n":
        "        if amount <= 0:\n            raise OrderError(\"refund must be positive\")\n"
        "        if order.refunded + amount > order.paid:\n            raise OrderError(\"refund exceeds payment\")\n",
}
NO_REORDER = {**GOOD, "        if order.status != \"refunded\" or order.shipped:\n":
              "        if True:\n"}
OVERWRITE = {k: v for k, v in GOOD.items() if "paid +=" not in v}
CATCHING_TEST = '''
import unittest
from orders.workflow import Order, OrderError, apply


class RulesTest(unittest.TestCase):
    def test_no_ship_after_partial_refund(self):
        o = Order(5000)
        apply(o, "pay")
        apply(o, "refund", 1)
        with self.assertRaises(OrderError):
            apply(o, "ship")
'''


class CheckingInvariantsChecks(unittest.TestCase):
    def run_check(self, check, edits=None, extra_test=False):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "orders-workflow"
            shutil.copytree(EVALS / "files" / "orders-workflow", work)
            text = WORKFLOW.read_text(encoding="utf-8")
            for old, new in (edits or {}).items():
                assert old in text, old
                text = text.replace(old, new, 1)
            (work / "orders" / "workflow.py").write_text(text, encoding="utf-8")
            if extra_test:
                (work / "tests" / "test_rules.py").write_text(CATCHING_TEST, encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / check)],
                               env={**os.environ, "EVAL_WORKDIR": str(work)},
                               capture_output=True, text=True, timeout=600)
            return r.returncode == 0

    def test_invariants(self):
        self.assertFalse(self.run_check("workflow_invariants.py"))
        self.assertTrue(self.run_check("workflow_invariants.py", GOOD))
        self.assertFalse(self.run_check("workflow_invariants.py", NO_REORDER))
        self.assertFalse(self.run_check("workflow_invariants.py", OVERWRITE))

    def test_tests_catch_original(self):
        self.assertFalse(self.run_check("tests_catch_original.py", GOOD))
        self.assertTrue(self.run_check("tests_catch_original.py", GOOD, extra_test=True))


@unittest.skipUnless(JAVA and Path(JAR).exists(), "needs java and tla2tools.jar (set TLA2TOOLS)")
class UploadModelCheck(unittest.TestCase):
    MODEL = EVALS / "files" / "upload-model" / "model" / "Upload.tla"
    CODE = EVALS / "files" / "upload-model" / "uploader" / "session.py"

    def run_check(self, model_edits=(), code_edits=()):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "upload-model"
            shutil.copytree(EVALS / "files" / "upload-model", work)
            for rel, edits in (("model/Upload.tla", model_edits), ("uploader/session.py", code_edits)):
                path = work / rel
                text = path.read_text(encoding="utf-8")
                for old, new in edits:
                    assert old in text, old
                    text = text.replace(old, new, 1)
                path.write_text(text, encoding="utf-8")
            r = subprocess.run([sys.executable, str(EVALS / "checks" / "model_kept_and_code_fixed.py")],
                               env={**os.environ, "EVAL_WORKDIR": str(work), "TLA2TOOLS": JAR},
                               capture_output=True, text=True, timeout=600)
            return r.returncode == 0

    def test_upload_model(self):
        model_fix = [('Cancel == /\\ state \\in {"uploading", "publishing"}', 'Cancel == /\\ state = "uploading"')]
        code_fix = [('if self.state not in ("uploading", "publishing"):', 'if self.state != "uploading":')]
        unpublish_model = [('Cancel == /\\ state \\in {"uploading", "publishing"}\n          /\\ state\' = "cancelled"\n          /\\ tempFile\' = FALSE\n          /\\ UNCHANGED published',
                            'Cancel == /\\ state \\in {"uploading", "publishing"}\n          /\\ state\' = "cancelled"\n          /\\ tempFile\' = FALSE\n          /\\ published\' = FALSE')]
        unpublish_code = [('        self.store.delete_temp(self.temp)\n        self.state = "cancelled"',
                           '        self.store.delete_temp(self.temp)\n        self.store.unpublish(self.name)\n        self.state = "cancelled"')]
        self.assertFalse(self.run_check())
        self.assertTrue(self.run_check(model_fix, code_fix))
        self.assertTrue(self.run_check(unpublish_model, unpublish_code))
        self.assertFalse(self.run_check(model_fix))
        weaken = [("CancelledIsUnpublished == state = \"cancelled\" => ~published",
                   "CancelledIsUnpublished == TRUE")]
        self.assertFalse(self.run_check(weaken, code_fix))
        drop = [("Next == Start \\/ Publish \\/ MarkCommitted \\/ Cancel \\/ Done",
                 "Next == Start \\/ Publish \\/ MarkCommitted \\/ Done")]
        self.assertFalse(self.run_check(drop, code_fix))


if __name__ == "__main__":
    unittest.main()
