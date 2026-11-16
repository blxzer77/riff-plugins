# API conventions

## Identifiers and timestamps

- IDs are strings with a type prefix: `cus_…`, `itm_…`.
- Timestamps are RFC 3339 in UTC.

## Authentication

Every endpoint requires a bearer token. Data is scoped to the caller's account; a
resource from another account is reported as 404, not 403.

## Errors

Errors use `application/problem+json` with the `Problem` schema: a stable `code`
that clients branch on, a human-readable `title`/`detail`, and the `request_id`
support asks for.

## Lists

Newer list endpoints return a page object `{ "data": [...], "next_cursor": ... }`,
take `limit` (1–100, default 25) and an opaque `cursor`, and document their sort
order. `GET /items` predates this convention and still returns a plain array.

## Clients

Mobile releases stay in use for months: about a fifth of mobile traffic comes from
app versions more than three releases old, and those versions cannot be changed.

## Changing the contract

Additive changes bump the minor version in `info.version`; breaking changes need a
new major version and a migration plan reviewed with the mobile team. Run
`python3 tests/check_contract.py` before you push.
