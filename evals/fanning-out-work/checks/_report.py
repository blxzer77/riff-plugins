"""Read per-slice verdicts out of the agent's final response.

A slice's verdict is the first status word that follows its name on a line. Lines
that start with the name (a table row or a list item, ignoring markup) are read
first; any other line counts only when no such line gives a verdict. Status words
are matched loosely because the prompt does not prescribe a vocabulary."""

import os
import re
import sys
from pathlib import Path

WORK = Path(os.environ["EVAL_WORKDIR"])
RESPONSE = WORK.parent / "response.md"

STATUS = [
    ("blocked", r"blocked|could\s*n[o']t\s+(?:be\s+)?(?:run|check(?:ed)?)|unable|not\s+(?:run|checked)|skipped|⚠️?|🚫"),
    ("fail", r"not\s+safe|unsafe|do\s+not\s+merge|don't\s+merge|fail(?:s|ed|ing|ure)?|issues?|broken|bad|red|reject(?:ed)?|❌|✗|✘|🔴"),
    ("pass", r"pass(?:es|ed|ing)?|ok|okay|green|good|clean|safe|succeed(?:s|ed)?|mergeable|✅|✓|✔️?|🟢"),
]
TOKEN = re.compile("|".join(f"(?P<{k}>(?<![\\w-])(?:{p})(?![\\w-]))" for k, p in STATUS), re.I)


LEAD = re.compile(r"^[\s|*\-+#>`_.:\d()\[\]]*")


def verdicts(names):
    text = RESPONSE.read_text(encoding="utf-8") if RESPONSE.exists() else ""
    lines = text.splitlines()
    found = {}
    for leading_only in (True, False):
        for line in lines:
            for name in names:
                if name in found:
                    continue
                if leading_only:
                    body = line[LEAD.match(line).end():]
                    m = re.match(rf"{re.escape(name)}(?![\w-])", body, re.I)
                    start = LEAD.match(line).end() + m.end() if m else None
                else:
                    m = re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", line, re.I)
                    start = m.end() if m else None
                if start is None:
                    continue
                t = TOKEN.search(line, start)
                if t:
                    found[name] = t.lastgroup
    return text, found


def fail(msg, detail=""):
    print(f"FAIL: {msg}")
    if detail:
        print(detail[-1200:])
    sys.exit(1)


def _files(root: Path):
    return {f.relative_to(root) for f in root.rglob("*")
            if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith(".pyc")}


def unchanged(fixture: Path, paths):
    """First path under `paths` that was edited, removed or added, or None."""
    for rel in paths:
        a, b = fixture / rel, WORK / rel
        if a.is_dir():
            before, after = _files(a), _files(b) if b.is_dir() else set()
            for f in sorted(before | after):
                if f not in before or f not in after or (a / f).read_bytes() != (b / f).read_bytes():
                    return str(Path(rel) / f)
        elif not b.is_file() or b.read_bytes() != a.read_bytes():
            return rel
    return None
