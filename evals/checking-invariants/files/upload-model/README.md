# uploader

Resumable uploads. `uploader/session.py` is the state machine; the upload worker
calls `start`, `write`, `publish`, `mark_committed`, and the UI may call `cancel`
at any time.

`model/Upload.tla` is a TLA+ model of the session, checked in CI with
`scripts/check-model.sh` (needs Java and `TLA2TOOLS` pointing at tla2tools.jar).
Tests: `python -m unittest`
