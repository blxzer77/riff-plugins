#!/bin/sh
cd "$(dirname "$0")"
status=0
for f in rates/*.csv; do
  if ! head -1 "$f" | grep -q '^currency,rate$'; then echo "billing: $f has a bad header"; status=1; fi
  if grep -q ',-' "$f"; then echo "billing: $f has a negative rate"; status=1; fi
done
exit $status
