#!/bin/sh
cd "$(dirname "$0")"
python3 -c "import json; json.load(open('config.json'))" && echo "auth: config ok"
