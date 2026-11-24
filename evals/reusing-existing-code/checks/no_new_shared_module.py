#!/usr/bin/env python3
"""Pass when the change adds no shared grab-bag module (utils, common, shared, core,
helpers, ...) directly under app/ that the fixture did not have."""
from pathlib import Path

from reuse_lib import FIXTURE, WORKDIR, finish

GRAB_BAG = {"utils", "util", "common", "shared", "helpers", "lib", "core", "misc"}


def top_modules(root: Path) -> set[str]:
    base = root / "app"
    if not base.is_dir():
        return set()
    return {p.stem for p in base.iterdir()
            if (p.is_dir() and p.name != "__pycache__") or (p.suffix == ".py" and p.stem != "__init__")}


added = sorted((top_modules(WORKDIR) - top_modules(FIXTURE)) & GRAB_BAG)
finish([f"new shared module(s): {', '.join('app.' + m for m in added)}"] if added else [],
       "no new shared grab-bag module")
