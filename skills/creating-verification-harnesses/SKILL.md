---
name: creating-verification-harnesses
description: Builds a project-local skill that lets any agent launch the app, drive it like a user and capture proof, and keeps it current. Use when a project has no scripted way to verify behavior end to end, or a verify skill or runbook fails or has drifted. Not for unit tests or CI setup.
license: Apache-2.0
metadata:
  verified-on: "2026-11-17"
---

# Creating verification harnesses

"Verify it in the app" is only a step an agent can take if the project tells it
how: start the app, know it is ready, use it the way a user does, keep proof, and
stop what it started. Write that once, as a project-local skill, and every later
change can be verified the same way. Write it for an agent that has never seen the
app and reads it mid-task.

## Build one

- [ ] **Interview the repository, not the user.** From the code, find: what users
      touch (web UI, API, CLI, desktop, library); how it starts locally (the
      project's own dev command, ports, environment, seed data, auth); how an agent
      can drive it (existing end-to-end tests first, then HTTP, a browser driver, a
      terminal session); what evidence it can capture (responses, output and exit
      codes, screenshots, stored state, logs); and whether two instances can run at
      once. Ask only what the code cannot answer.
- [ ] **Never drive real data.** Point every run at a throwaway data directory,
      database, file or account, and a port nobody else uses. If the app cannot be
      isolated, say so in the skill and refuse to drive a shared instance.
- [ ] **Write the skill** where the project's agents load skills (for example
      `.agents/skills/verify-<app>/SKILL.md`), with frontmatter naming the app and
      when to use it, and these sections, using real commands from this repository:
  - **Launch:** the exact command, and how to tell it is ready to use, not merely
    running. For a short-lived CLI there is nothing to launch: build or install once
    and give each check its own isolated state.
  - **Doctor:** one read-only check that this instance is the right one: up, the
    expected version, the throwaway data, started by this run. Run it before
    driving and after anything surprising.
  - **Drive:** recipes per feature, through the paths users take, with stable
    handles (routes, command names, accessible labels), each with the observable
    result that proves it.
  - **Evidence:** what to capture (the action and the resulting state, side effects
    such as stored values) and where it goes. When a safe mode such as `--dry-run`
    is used, record what it actually skipped.
  - **Cleanup:** stop only what this run started, by recorded PID or container id,
    never by process name. Cleanup keeps the evidence.
  - **Helpers:** any script the skill ships is executable and its invocation is in
    the skill body.
- [ ] **Map the features.** One short file per user-facing feature (start with the
      top three to five): what it does, every way a user reaches it, how to drive
      it, and the traps. If a precondition is missing, the recipe reports it; it is
      not weakened to pass.
- [ ] **Prove the skill before handing it over.** Follow it exactly once: launch,
      doctor, drive one feature, capture evidence, clean up, then confirm the
      evidence still exists and nothing is left running. A skill nobody ran is a
      draft. If you proved it somewhere other than the real target (a container for
      a VM), list what that stand-in did that the target will not.

## Keep one current

When a verify skill fails, or the app changed since it was written:

- [ ] Run it live as written, from Launch to Cleanup, on throwaway data.
- [ ] For each failure, decide which it is: **drift** (the app changed on purpose;
      fix the skill or its feature map), **harness gap** (working behavior the
      recipe cannot drive; fix the recipe), or **product bug** (the app is broken;
      report it, do not paper over it in the docs).
- [ ] Edit only the skill's own folder. Never change product code to match the
      skill.
- [ ] Rerun every corrected step live before calling it fixed, then clean up.

## Report

```text
Skill: <path>, sections written or changed
Proved: <launch, doctor, feature driven, evidence path> -> <what each showed>
Isolation: <throwaway data and port used; real data untouched>
Drift / gaps / bugs: <each, with the fix or the report>
Not covered: <features, platforms or real targets not exercised>
```

## Gotchas

- The README's default command is often the one that touches real data (`./data`,
  the team's database). Read the defaults before the first launch.
- A health endpoint that answers is not proof the instance is yours: check the
  version and the data location it reports.
- Killing by process name stops other people's servers and agents. Record the PID.
- Recipes that drive internal setters or test-only endpoints prove the internals,
  not what users get.

## References

- `references/sources.md` — the guidance this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file so agents use the verify skill.
