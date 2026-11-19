#!/usr/bin/env python3
"""long-page: the second segment was read with the printed continuation
(`--range <end>-`), and the page was not fetched again from the start."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _calls import calls, fetched, finish  # noqa: E402

page = fetched("docs.example.dev/cargo/pinning")
continued = [call for call in page if "--range" in call or any(w.startswith("--range=") for w in call)]
fresh = [call for call in page if call not in continued]
finish(
    bool(continued) and len(fresh) <= 1,
    "read the rest of the page with the continuation command",
    "never read past the first segment, or refetched the page from the start",
    f"calls: {calls()}",
)
