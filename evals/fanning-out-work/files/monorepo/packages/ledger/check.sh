#!/bin/sh
cd "$(dirname "$0")"
python3 - <<'PY'
entries = [l.split(",") for l in open("entries.csv").read().split()[1:]]
assert sum(int(a) for _, a in entries) == 0, "ledger does not balance"
print("ledger: balanced")
PY
