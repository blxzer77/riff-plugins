---
name: verifying-changes
description: "Proves a change works by running it the way it really runs. Use when implementing a feature, fix, default or config change and before saying it works, when someone says a fix is done, or when tests pass but real behavior is unconfirmed. Not for writing tests, reading a diff for bugs, or debugging."
license: Apache-2.0
metadata:
  verified-on: "2026-11-17"
---

# Verifying changes

"Done" means the behavior the user asked for now happens, not that the code
compiled, the tests passed, or the diff looks right. Those are proxies: tests cover
what someone thought to test, a type check proves shapes, and a setting can be
overridden somewhere you did not look. Before reporting, exercise the change the
way it will actually run, and say plainly what you could not exercise.

## Workflow

- [ ] **State the observable result.** Turn the request into something you can see:
      "`python -m notes list` prints JSON", "a session idle 20 minutes is still
      valid", "a 503 is retried and then succeeds". Pick the entry point a user or
      caller actually uses.
- [ ] **Find everything that decides that result.** Search beyond the line you plan
      to change: configuration files, environment variables, a second copy of a
      constant, middleware, templates, feature flags, callers in other languages.
      A search that finds one definition has not shown it is the one used.
- [ ] **Make the change, then run the real entry point.** Run the command, call the
      function the way its callers do, hit the endpoint, render the page. Read the
      output; do not infer it. Run the existing tests too, but as a separate check.
      Make sure what runs is what you changed: a bundle, a build directory, an
      installed package, or a server that was already running can still hold the
      old code. Rebuild, reinstall or restart the way the project does.
- [ ] **Exercise the edges the request implies.** The old behavior still available
      when it should be (`--format table`), the limit on both sides (20 and 31
      minutes), the failure the change is for (a 503, a reset), and the failure it
      must not swallow (a 400).
- [ ] **Fake only what you cannot reach.** When the real dependency is unavailable
      (production storage, a paid API, hardware), drive the code with a fake or a
      local server that produces the same responses, and say so in the report.
- [ ] **Report with evidence.** For each claim, give the command and the relevant
      output. List what was not verified and why.

## What counts as evidence

- **Give each claim a verdict:** verified, not verified, or inconclusive.
  Inconclusive is not a pass.
- **Run the same check on both sides.** A check is evidence only if it gives a
  different result without the change. For a fix, yours or someone else's, first
  reproduce the reported symptom on the old code with the reporter's input, command
  and environment, then run the identical check on the fix. If the old code does not
  show the symptom, there is no baseline: the verdict is inconclusive, saying which
  side could not be measured. If the fix still shows it, the fix is insufficient.
  Capture the final state that differs, not a setup step or a loading screen.
- **Watch a safe mode work.** A `--dry-run`, test mode or `--check` flag proves
  nothing by its name. Compare the files, git refs, stored data and network calls
  before and after a run.
- **Read back after acting.** After a merge, deploy, publish or migration, read the
  resulting state. A command that reports success may only have queued the work.
- **Name what a stand-in hides.** A fake, a local server or a container proves the
  code against that stand-in. Under Not verified, list what the real target does
  differently: authentication, limits, data, setup the stand-in did for you.
- **A verdict covers the code it ran against.** After a fix round, a rebase or a
  review edit, run the check again, scaled to what changed.
- **Prefer a checker who did not write the change** when you can hand the
  verification to another agent or person; an author checks what they meant to build.
- **Leave the environment as you found it.** Stop only the processes you started,
  and keep the evidence.

## Report

```text
Changed: <files and what each change does>
Verified: <claim> -- <command or call> -> <output that shows it>
Also checked: <edges, old behavior kept, tests run and their result>
Not verified: <claim, and why: real service, other OS, production data, stand-in gaps>
Inconclusive: <claim, what was tried, what would settle it>
```

If something you expected to see did not appear, say so first; do not report done.

## Gotchas

- Passing tests prove only what they assert. A test that reads the setting you just
  changed passes even when the code that enforces it uses a different number.
- A default in code is often overridden by a shipped config file, an environment
  variable, or a database row. Check what the running program actually reads.
- Run the check after the last edit. An earlier run says nothing about the final
  code.
- "It should work" and "the logic is correct" are predictions. Either run it or put
  it under Not verified.
- A check someone else ran may pass on the old code too. Run it there before
  counting it; for your own change, break the change on purpose once.

## References

- `references/sources.md` — the guidance this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file for always-on verification defaults.
