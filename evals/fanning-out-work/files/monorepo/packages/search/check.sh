#!/bin/sh
cd "$(dirname "$0")"
test "$(wc -l < stopwords.txt)" -ge 3 && echo "search: stopwords ok"
