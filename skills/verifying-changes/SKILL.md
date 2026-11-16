---
name: verifying-changes
description: "Proves a change works by running it the way it really runs. Use when implementing a feature, fix, default or config change and before saying it works, or when tests pass but the real behavior is unconfirmed. Not for writing test suites, reviewing someone else's diff, or debugging."
license: Apache-2.0
metadata:
  verified-on: "2026-11-16"
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
- [ ] **Exercise the edges the request implies.** The old behavior still available
      when it should be (`--format table`), the limit on both sides (20 and 31
      minutes), the failure the change is for (a 503, a reset), and the failure it
      must not swallow (a 400).
- [ ] **Fake only what you cannot reach.** When the real dependency is unavailable
      (production storage, a paid API, hardware), drive the code with a fake or a
      local server that produces the same responses, and say so in the report.
- [ ] **Report with evidence.** For each claim, give the command and the relevant
      output. List what was not verified and why.

## Report

```text
Changed: <files and what each change does>
Verified: <command or call> -> <output that shows the requested behavior>
Also checked: <edges, old behavior kept, tests run and their result>
Not verified: <what could not run here (real service, other OS, production data)>
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
- When a check passes immediately, make sure it can fail: break the change on
  purpose once, or check the old behavior fails the same check.

## References

- `references/sources.md` — the guidance this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file for always-on verification defaults.
