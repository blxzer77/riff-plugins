#!/usr/bin/env python3
"""unconfigured: after exit 3 the agent stops calling riff for the web (at
most one more attempt) and tells the user it needs configuring."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _calls import answer, calls, finish  # noqa: E402

web_calls = [call for call in calls() if call[:2] in (["web", "search"], ["web", "fetch"])]
text = answer().lower()
told = re.search(r"riff init|config(ure|uration)?\b|\.riff|not (set up|configured)", text) is not None
finish(
    1 <= len(web_calls) <= 2 and told,
    "stopped after the configuration error and told the user to configure riff",
    "kept retrying riff, or did not tell the user it needs configuring",
    f"calls: {calls()}\nanswer: {text[-600:]}",
)
