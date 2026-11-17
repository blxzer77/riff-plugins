# TLA+ quickstart

Enough TLA+ to model a few actors and check a safety property with TLC. Verified
with TLC from `tla2tools.jar` v1.7.4 on Java 25, 2026-11-17.

## A worked template

Two clients withdraw from one account. In the code each withdrawal is two store
calls, read then write, so the model has two actions per client, and a program
counter `pc` says which step each client is at.

```tla
---- MODULE Withdraw ----
EXTENDS Naturals
CONSTANTS Clients, Amount, Start
VARIABLES balance, pc, seen, paidOut
vars == <<balance, pc, seen, paidOut>>

Init == /\ balance = Start
        /\ pc = [c \in Clients |-> "read"]
        /\ seen = [c \in Clients |-> 0]
        /\ paidOut = 0

\* bank.py: withdraw(), b = store.get("balance")
Read(c) == /\ pc[c] = "read"
           /\ seen' = [seen EXCEPT ![c] = balance]
           /\ pc' = [pc EXCEPT ![c] = IF balance >= Amount THEN "write" ELSE "done"]
           /\ UNCHANGED <<balance, paidOut>>

\* bank.py: withdraw(), store.put("balance", b - amount)
Write(c) == /\ pc[c] = "write"
            /\ balance' = seen[c] - Amount
            /\ paidOut' = paidOut + Amount
            /\ pc' = [pc EXCEPT ![c] = "done"]
            /\ UNCHANGED seen

\* Legitimate end state: everyone finished.
Done == /\ \A c \in Clients : pc[c] = "done"
        /\ UNCHANGED vars

Next == Done \/ \E c \in Clients : Read(c) \/ Write(c)
Spec == Init /\ [][Next]_vars

\* The bank never pays out more than the account held.
NoOverdraw == paidOut <= Start
====
```

`Withdraw.cfg`:

```text
CONSTANTS Clients = {c1, c2}
          Amount = 70
          Start = 100
SPECIFICATION Spec
INVARIANT NoOverdraw
```

TLC reports `Invariant NoOverdraw is violated` with the trace Read, Read, Write,
Write: both clients read 100 before either writes, and 140 is paid out.

## Patterns

- **One atomic step per action.** A read and a later write are two actions. A
  compare-and-set is one action whose guard is the comparison.
- **Many actors.** Give each actor its own `pc[c]` and local copies (`seen[c]`), and
  write `Next` as `\E c \in Clients : ...`.
- **Time and expiry.** Model a lease as a value plus an `expired` flag, and add an
  `Expire` action that may fire at any time once the lease is held. That covers any
  pause longer than the timeout without modeling clocks.
- **Crashes and retries.** Add `Crash(c)` that resets the actor's `pc` and local
  state but not the shared store, and a `Retry` path from where the code retries.
- **Messages.** Keep a set (or a bag) of messages in flight; delivery is an action
  that may pick any message, so reordering and duplicates come for free.
- **End states.** Add a `Done` action that changes nothing, as above, or run TLC with
  `-deadlock`.
- **Bounds.** Keep constants small. For counters that could grow forever, add
  `CONSTRAINT` with a predicate such as `retries <= 3` to the config.

## Config file

```text
CONSTANTS Workers = {w1, w2}     \* model values: bare names
SPECIFICATION Spec               \* or INIT Init and NEXT Next
INVARIANT TypeOK Safe            \* one or more state predicates
CONSTRAINT Bound                 \* optional: do not explore past this predicate
```

## Reading the output

- `Model checking completed. No error has been found.` means every reachable state
  within the bounds satisfies every invariant.
- `Error: Invariant X is violated.` is followed by `State 1`, `State 2`, ... each
  naming the action that produced it and the value of every variable. That trace is
  the shortest path TLC found; replay it on the real code.
- `Error: Deadlock reached.` means a state with no enabled action. Decide whether it
  is a real hang or a legitimate end state that needs a `Done` action.
- `Attempted to ...` or parse errors come from the model, not from the system.
