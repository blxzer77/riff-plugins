---
name: verify-notesapp
description: Launches notesapp on a throwaway data directory and drives its API and CLI like a user to prove a change works. Use when verifying any change to notesapp.
---

# Verify notesapp

## Launch

```sh
export VERIFY_DIR=$(mktemp -d)
python -m notesapp serve --port 18999 --data "$VERIFY_DIR/data" > "$VERIFY_DIR/server.log" 2>&1 &
echo $! > "$VERIFY_DIR/server.pid"
export NOTES_URL=http://127.0.0.1:18999
```

Ready when the Doctor check passes.

## Doctor

```sh
curl -fsS "$NOTES_URL/health"
```

Expect `"ok": true` and `"data"` pointing at `$VERIFY_DIR/data`, never `./data`.

## Drive

Follow the matching file in `features/`.

## Evidence

Save command output under `$VERIFY_DIR/evidence/` and copy that folder to
`./verify-evidence/<date>/` before cleanup.

## Cleanup

```sh
kill "$(cat "$VERIFY_DIR/server.pid")"
```

Kill only the server this run started. Keep `./verify-evidence/`.
