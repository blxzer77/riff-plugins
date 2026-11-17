---
name: checking-invariants
description: "Checks promises tests rarely reach by exploring every case in a bound, with a TLA+ model checker or by enumerating states. Use when races, retries, leases, event orderings, state machines or protocols must never fail, when asked if X can ever happen, or a model check fails. Not for routine tests."
license: Apache-2.0
metadata:
  verified-on: "2026-11-17"
---

# Checking invariants

A test checks the cases someone thought of. Bugs in concurrent, retried or
event-driven code live in the orderings nobody thought of. Checking every case
within a bound finds them: every interleaving of a small model, every sequence of
events up to a depth, every input in a range. The result is either a
counterexample you can replay or a pass whose bounds you can state.

## Workflow

- [ ] **State the promise.** Write it once in the words of the person who relies on
      it ("a job never runs on two workers at once") and once as a predicate over
      state. Name the bad state exactly. Never weaken the promise to make a check pass.
- [ ] **Pick the cheapest tool that answers the question.** If the repository
      already has a model or a checker, use and extend it.

      | Question | Tool |
      |---|---|
      | Can the steps of several actors (workers, retries, UI and background) interleave badly? Is a design safe before it is built? | A model checker on a small model; TLA+ with TLC is the default in any language |
      | Can some sequence of events or calls break the real code? | Enumerate every sequence up to a depth against the code, or a stateful property-based test |
      | Does it hold for every input? | Generated inputs against the real code; exhaustive for small domains |
      | Must it hold at every size? | A proof; say that a bounded check is not one |

- [ ] **Make the model true to the code or the design.** One action is one atomic
      step: one store call, one message, one method. Two calls modeled as one action
      hide the race. Name actions after the code and point each at its file and
      function. Give the environment its full freedom: any actor at any time, crashes,
      expiry, retries, duplicate delivery. Keep constants small (two workers, two
      jobs) and bound anything unbounded.
- [ ] **See the check fail.** Run it on a variant you know is broken, or on the
      current code when you suspect a bug. A check never seen failing proves nothing.
- [ ] **Replay each counterexample on the real code**, step by step, as a test. If
      a step cannot happen in the code, the model is wrong: fix it and say what was
      wrong. If every step can happen, it is a bug. For a design not built yet, give
      the interleaving in the design's own terms.
- [ ] **Fix, then update the model from the code.** Change the code, then make the
      model describe the fixed code, then rerun. Do not shape the model by what makes
      it pass. Change the promise only when it changed on purpose, and cite the
      evidence (a spec, a ticket, the owner's words).
- [ ] **Leave it runnable.** One command, a pinned tool version, a run short enough
      to repeat on every relevant change. Record which code each check covers and
      the commit it was last confirmed against, so later edits show when it needs
      another look.

## Running TLC

TLC ships in `tla2tools.jar` (GitHub `tlaplus/tlaplus` releases; v1.7.4 here) and
needs Java 11 or later. Read `references/tla-quickstart.md` before writing a model.

```sh
java -XX:+UseParallelGC -cp tla2tools.jar tlc2.TLC -workers 1 -config Spec.cfg Spec
```

- TLC stops at the first broken invariant. To learn about the others, remove it
  from the config and run again.
- A state with no next step is reported as a deadlock. For legitimate end states,
  add an action that leaves everything unchanged there, or pass `-deadlock` to skip
  the deadlock check.
- Write `Next` as a disjunction of named actions, so the trace names each step.
- `-workers 1` keeps runs and traces repeatable.

## Report

```text
Promise: <plain sentence> / <predicate>
Checked with: <tool, model or harness path, bounds (actors, depth, input range)>
Result: holds within these bounds | broken
Counterexample: <numbered steps in the code's or design's terms; the test that replays it>
Fix: <code change; model change; promise unchanged, or changed with evidence>
Not covered: <what the model leaves out: timing, crash points, other actors, larger sizes>
Rerun: <one command>
```

## Gotchas

- A pass covers the model and the bounds, not the system.
- A red model check in CI is a finding. Do not delete the invariant, drop the
  action, or add a constraint to get green; fix the code or show the model wrong.
- After a change, a check that passes at once may have lost the ability to fail.
  Break the new code on purpose and confirm it is caught.
- Check safety ("nothing bad happens") first. Liveness ("something good eventually
  happens") needs fairness assumptions and is easy to state wrongly.
- Example-based tests written after the fact pin the bugs you found; keep the
  systematic check too, so the next ordering is caught.

## References

- `references/tla-quickstart.md` — read before writing or editing a TLA+ model: a worked two-actor template, config syntax, reading traces.
- `references/sources.md` — the sources this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file when the project keeps models or invariant checks.
