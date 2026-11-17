# Job lease

Status: proposed. Owner: platform team.

## Goal

Any number of workers poll the same queue. A job must never run on two workers at
the same time: some jobs send email or charge cards.

## Store

The lease lives in our key-value store, which offers:

- `get(key)` returns the value, or nothing if the key is missing or expired.
- `put(key, value, ttl)` writes the value with an expiry, replacing what is there.
- `delete(key)`.

Each call is atomic on its own. There is no transaction across calls.

## Protocol

Lease key: `lease:<job id>`. Lease value: the worker id. TTL: 30 seconds.

**Acquire.** A worker that picks job J:

1. `get(lease:J)`. If a lease exists, skip J.
2. `put(lease:J, me, 30s)`.
3. `get(lease:J)` again. If the value is `me`, the worker owns J and starts it.
   Otherwise another worker won; skip J.

**Renew.** Every 10 seconds while running J:

1. `get(lease:J)`. If the value is not `me`, stop working on J immediately.
2. `put(lease:J, me, 30s)`.

**Finish.** Write the result, then `delete(lease:J)`.

## Why this is safe

Acquire reads the lease back after writing it, so only the worker whose write
landed last starts the job. Renew checks the holder before extending, so a worker
that lost its lease stops at its next renewal. Therefore at most one worker runs a
job at any time.

## Operations

Workers are JVM services; rare GC pauses of up to 45 seconds have been observed.
