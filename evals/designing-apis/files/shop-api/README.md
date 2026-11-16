# Shop API

The public HTTP API for the shop's web app, mobile apps (iOS/Android 3.x and later),
and partner integrations.

- `openapi.json` is the contract and the source of truth. Server stubs and the
  client SDKs are generated from it when we release.
- `docs/conventions.md` describes the conventions every endpoint follows.
- `python3 tests/check_contract.py` checks the contract; run it after every change.
