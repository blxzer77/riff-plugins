#!/bin/sh
cd "$(dirname "$0")"
echo "notify: templates OK"
missing=0
for t in welcome reset; do [ -f "templates/$t.txt" ] || missing=1; done
exit $missing
