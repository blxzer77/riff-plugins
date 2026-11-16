---
name: debugging-failures
description: Finds and fixes the root cause of a failure. Use when something crashes, gives wrong output, fails a test or a job, or a user reports a bug whose cause is not known yet, even if they offer a guess. Not for adding features, performance tuning, flaky-test cleanup or reviewing a diff.
license: Apache-2.0
metadata:
  verified-on: "2026-11-16"
---

# Debugging failures

A fix is only as good as the explanation behind it. Bad fixes make the symptom go
away without anyone being able to say why it appeared: a broader `catch`, a retry,
a default value, a patch in the caller that displayed the wrong number. Find the
first place the program did something wrong, show it with evidence, fix it there,
and show that the original failure is gone.

## Workflow

- [ ] **Restate the failure.** Write down what happened and what should have
      happened, the exact error and where it was raised, the input, and the
      command. The reporter's guess about the cause ("probably encoding") is a
      hypothesis to test, not a fact; when the evidence contradicts it, say so.
- [ ] **Reproduce it before changing code.** Run the user's command or the real
      entry point and see the reported error. If it needs conditions you lack
      (production data, a dropped connection), build the smallest case that
      triggers the same mechanism: one fixture row, a fake dependency that raises
      exactly what the log shows. Put it in a test when a test can hold it, run it,
      and see it fail for the reported reason before you edit the code.
- [ ] **Find the cause.** Work back from the symptom to where the wrong value or
      decision first appears. Treat each idea as a hypothesis and rule it in or out
      by running code and reading the actual state, changing one thing at a time.
      When a known good version exists, bisect. Stop at a decision in the code that
      is wrong in itself, not one that only passes on an earlier mistake.
- [ ] **Fix it at the origin.** Ask whether the state that broke the code is
      legitimate. If it is, handle it where it broke. If it should never exist, fix
      what produced it; a guard at the crash site only hides it.
- [ ] **Look for the same fault elsewhere.** Search the other callers of the broken
      code and other copies of the pattern. Name who else was affected: another
      endpoint or job, data already written wrong, a long-running process that
      keeps the bad state until restarted.
- [ ] **Verify with the original reproduction.** The command or test that failed now
      passes, for the reason you fixed, and the rest of the suite passes. If you
      cannot rerun the original, say what you ran instead.

## Do not hide the failure

- Keep error handling as narrow as the problem. Retry, catch or fall back only for
  the condition that is legitimately expected (the error the dependency marks as
  transient), never for everything it can raise. Widening a narrow condition
  retries declines, re-sends payments, or hides the next bug.
- Do not get past bad input by dropping it (skipping rows, `errors="ignore"`, a
  default value) unless the user asked for lossy behavior. A malformed record that
  used to fail loudly must still fail.
- Do not correct the value where it is displayed when the code producing it is
  wrong; every other caller still gets the wrong value.
- When evidence refutes a hypothesis, revert what it motivated. Ship only changes
  the evidence supports.
- If you cannot reproduce the failure, say so. Report what you tried, the leading
  hypothesis, and what evidence would confirm it; add a diagnostic if it helps. Do
  not present a speculative change as the fix.

## Report

```text
Cause: <the wrong decision, file:line, and how the reported input reaches it>
Evidence: <the reproduction failing before and passing after: commands and output>
Fix: <what changed, and why there>
Also affected: <other callers, data, processes; or "none found" and how you searched>
Not verified: <what you could not reproduce or run>
```

When the user's guess was wrong, say so in the first lines of the report.

## Gotchas

- The line in a traceback is where the failure surfaced, not where it started. An
  unpacking error at a `split` can be a quoting rule the parser never handled.
- A failure that appears only after a restart points at persisted state first:
  configuration, caches, lock files, serialized data.
- A failure that comes and goes has a condition you have not found yet: input
  order, time, concurrency, state shared between calls or tests. Find what makes it
  happen every time before fixing. For flaky tests, use writing-tests.
- Line numbers in a production traceback that do not match the repository mean the
  deployed code differs. Say so; the fix may not reach what failed.
- A regression test that was never seen failing proves nothing about the fix.

## References

- `references/sources.md` — the debugging literature this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file for always-on debugging defaults.
