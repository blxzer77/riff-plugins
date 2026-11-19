#!/usr/bin/env bash
# Type-checks pi/extensions/riff-web.ts against an installed pi.
#
# The extension imports pi's own types and `typebox`; both ship inside the pi
# package, and there is no npm dependency of our own, so this checks against
# whatever pi is installed rather than a pinned copy. That is the point: the
# types are the contract the extension must match.
#
# Usage: scripts/check-pi-extension.sh [path-to-pi-package]
#   Default: the global npm install under the active node's lib/node_modules.
#   Exits 0 with a note when no pi install is found (CI without node+pi).
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
pi_pkg=${1:-}

if [[ -z "$pi_pkg" ]]; then
  for candidate in \
    "$(dirname "$(command -v node 2>/dev/null || echo /nonexistent)")/../lib/node_modules/@earendil-works/pi-coding-agent" \
    "$HOME/.nvm/versions/node/"*/lib/node_modules/@earendil-works/pi-coding-agent; do
    if [[ -d "$candidate" ]]; then
      pi_pkg=$candidate
      break
    fi
  done
fi

if [[ -z "$pi_pkg" || ! -d "$pi_pkg" ]]; then
  echo "skip: no installed pi package found (scripts/check-pi-extension.sh <path> to point at one)"
  exit 0
fi

for file in dist/index.d.ts node_modules/typebox/build/index.d.mts; do
  [[ -f "$pi_pkg/$file" ]] || { echo "skip: $pi_pkg lacks $file" >&2; exit 0; }
done

work=$(mktemp -d "$repo/target/test-tmp/pi-tscheck.XXXXXX")
trap 'rm -rf "$work"' EXIT

cat > "$work/tsconfig.json" <<EOF
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "skipLibCheck": true,
    "types": [],
    "baseUrl": ".",
    "paths": {
      "@earendil-works/pi-coding-agent": ["$pi_pkg/dist/index.d.ts"],
      "typebox": ["$pi_pkg/node_modules/typebox/build/index.d.mts"]
    }
  },
  "files": ["$repo/pi/extensions/riff-web.ts"]
}
EOF

cd "$work"
npx --yes -p typescript@5 tsc -p tsconfig.json
echo "ok: pi/extensions/riff-web.ts type-checks against $(node -p "require('$pi_pkg/package.json').version" 2>/dev/null || echo pi)"
