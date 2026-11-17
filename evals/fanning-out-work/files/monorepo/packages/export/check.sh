#!/bin/sh
cd "$(dirname "$0")"
command -v xsv >/dev/null || { echo "export: xsv is required (cargo install xsv)" >&2; exit 127; }
xsv headers sample.csv | grep -q id && echo "export: sample ok"
