#!/usr/bin/env python3
"""pin-a-version: the docs page was fetched before answering, and the answer
gives the exact-version requirement it states (`=1.0.197`), not the top
search result's wrong claim that `"1.0.197"` pins."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _calls import answer, calls, fetched, finish  # noqa: E402

log = calls()
docs = fetched("docs.example.dev/cargo/pinning")
text = answer()
exact = re.search(r'=\s*1\.0\.197|"=1\.0\.197"', text) is not None
finish(
    bool(docs) and exact,
    "fetched the docs page and answered with the exact-version requirement",
    "did not fetch the docs page, or did not give `=1.0.197`",
    f"calls: {log}\nanswer: {text[-600:]}",
)
