---
name: fanning-out-work
description: "Splits work into independent slices or competing attempts, runs them in parallel or in turn, and merges one report you can trust. Use when checking many packages, files, patches, commits or services, or racing alternatives to pick one. Not for a single change, or debugging one failure."
license: Apache-2.0
metadata:
  verified-on: "2026-11-17"
---

# Fanning out work

Splitting work across workers (subagents, parallel sessions, or plain sequential
runs) makes coverage cheap and makes it easy to lose track. A slice that never
reported looks like a pass. Two attempts applied to one tree contaminate each
other. A pile of raw outputs is not an answer. The protocol below keeps the result
trustworthy whether the slices run in parallel or one after another.

## Workflow

- [ ] **Frame.** State what done means and what the final report must contain.
      Choose the shape: **slices** (cover every package, file, patch or commit) or a
      **race** (several attempts at one task, one winner), or both. For a race,
      write the selection rule before seeing any result, such as "every case
      correct, then fastest" or "first to pass".
- [ ] **List the slices.** Name every one explicitly. The list is the coverage
      contract; the report must account for each entry.
- [ ] **Isolate.** A worker that writes, builds or applies anything gets its own
      copy (a directory, a worktree, a branch). Never apply candidates one after
      another to one tree and judge each in the state the previous one left.
      Read-only workers may share.
- [ ] **Brief each worker so it stands alone.** Goal, its slice, how to verify, and
      what to return, plus the exact inputs: paths, commit SHAs, and for a
      measurement the method (what one sample is, how many, in what order). The
      worker sees only the brief. Ask for one of **PASS**, **ISSUES** (every
      problem it can show, not only the first) or **BLOCKED** (could not check,
      and why), each with evidence.
- [ ] **Fan out.** Start all workers at once when the agent can run parallel
      workers; otherwise run the same briefs one after another. One level only:
      workers do not start workers unless the plan says so.
- [ ] **Aggregate.** Every listed slice needs a result. A result missing the
      requested evidence or inputs gets one retry; a second miss is a gap. Gaps
      and BLOCKED are not passes. For a race, measure every attempt the same way
      and apply the rule declared up front.
- [ ] **Report** in the format below. Do not paste raw worker output.

## Report

```text
Scope: <what was checked, against which version, how>
| slice | verdict | evidence (one line) |
Issues: <one line each: slice, problem, where>
Gaps: <slices with no usable result, blocked slices and what they need>
Race rule: <the rule, the ranking, the winner> (races only)
```

## Gotchas

- Exit codes beat printed text. A check that prints "OK" and exits non-zero failed.
- A slice that could not run (missing tool, credentials, data) is BLOCKED. It is
  neither a defect in that slice nor a pass.
- Workers asked to check do not fix. Fixes are a separate step after the report.
- Results that depend on order (patches touching the same lines, migrations) are
  findings of their own: report them next to the per-slice verdicts.
- Leave the shared tree as it was and remove the copies you made.

## References

- `references/sources.md` — the guidance this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file when agents often run sweeps or parallel checks.
