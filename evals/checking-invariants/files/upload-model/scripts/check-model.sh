#!/bin/sh
# Model-check model/Upload.tla with TLC. CI runs this on every push.
set -e
: "${TLA2TOOLS:?set TLA2TOOLS to the path of tla2tools.jar}"
cd "$(dirname "$0")/../model"
exec java -XX:+UseParallelGC -cp "$TLA2TOOLS" tlc2.TLC -workers 1 -cleanup -config Upload.cfg Upload
