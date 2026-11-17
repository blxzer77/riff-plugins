#!/usr/bin/env python3
"""upload-model: the promise and the Cancel action stay in the model, TLC passes, and the
real code no longer lets a cancelled upload leave a published file."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"])
FIXTURE = Path(__file__).resolve().parent.parent / "files" / "upload-model"
JAR = os.environ.get("TLA2TOOLS") or str(Path.home() / ".cache/riff-skills/tools/tla2tools-1.7.4.jar")


def fail(msg, detail=""):
    print(f"FAIL: {msg}")
    if detail:
        print(detail[-1500:])
    sys.exit(1)


def strip(tla):
    tla = re.sub(r"\(\*.*?\*\)", "", tla, flags=re.S)
    return re.sub(r"\\\*.*", "", tla)


def definition(tla, name):
    m = re.search(rf"^{name}\s*==(.*?)(?=^\S|\Z)", strip(tla), flags=re.S | re.M)
    return " ".join(m.group(1).split()) if m else None


spec = (WORK / "model" / "Upload.tla").read_text(encoding="utf-8") if (WORK / "model" / "Upload.tla").exists() else ""
original = (FIXTURE / "model" / "Upload.tla").read_text(encoding="utf-8")
if definition(spec, "CancelledIsUnpublished") != definition(original, "CancelledIsUnpublished"):
    fail("the promise CancelledIsUnpublished was changed or removed",
         str(definition(spec, "CancelledIsUnpublished")))
cfg = (WORK / "model" / "Upload.cfg").read_text(encoding="utf-8") if (WORK / "model" / "Upload.cfg").exists() else ""
if not re.search(r"INVARIANTS?\b[^\n]*\bCancelledIsUnpublished\b", strip(cfg)):
    fail("Upload.cfg no longer checks CancelledIsUnpublished", cfg)
nxt = definition(spec, "Next") or ""
if not definition(spec, "Cancel") or not re.search(r"\bCancel\b", nxt):
    fail("the model no longer lets the UI cancel (Cancel is gone from Next)", nxt)

if not Path(JAR).exists():
    fail(f"no tla2tools.jar at {JAR} (set TLA2TOOLS)")
tmp = Path(tempfile.mkdtemp(prefix="upload-check-")) / "work"
shutil.copytree(WORK, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__", "states"))
r = subprocess.run(["sh", "scripts/check-model.sh"], cwd=tmp, capture_output=True, text=True, timeout=300,
                   env={**os.environ, "TLA2TOOLS": JAR})
out = r.stdout + r.stderr
if r.returncode != 0 or "No error has been found" not in out:
    fail("scripts/check-model.sh does not pass", out)

probe = r'''
import os, unittest
from uploader.session import Session, UploadError
from uploader.store import MemoryStore

store = MemoryStore()
s = Session(store, "report.pdf")
s.start(); s.write(b"abc"); s.publish()
try:
    s.cancel()
except UploadError:
    pass
assert not (s.state == "cancelled" and "report.pdf" in store.published), (s.state, store.published)
if s.state == "publishing":
    s.mark_committed()
    assert s.state == "committed" and store.published["report.pdf"] == b"abc"

store = MemoryStore(); s = Session(store, "a"); s.start(); s.write(b"x"); s.cancel()
assert s.state == "cancelled" and store.published == {} and store.temp == {}
store = MemoryStore(); s = Session(store, "b"); s.start(); s.write(b"y"); s.publish(); s.mark_committed()
assert s.state == "committed" and store.published == {"b": b"y"} and store.temp == {}
r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.defaultTestLoader.discover("tests", top_level_dir="."))
assert r.wasSuccessful(), (r.failures, r.errors)
'''
r = subprocess.run([sys.executable, "-c", probe], cwd=tmp, capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    fail("the code still lets a cancel during publishing leave a published file", r.stdout + r.stderr)
print("PASS: promise and Cancel kept, TLC passes, and the code no longer publishes cancelled uploads")
