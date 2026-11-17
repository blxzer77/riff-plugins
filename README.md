# riff-skills

Agent Skills for software engineering work that agents tend to skip or get wrong:
writing tests, recording decisions, choosing technologies, drawing module and API
boundaries, reviewing code and designs, and building LLM applications.

Every skill follows the open [Agent Skills specification](https://agentskills.io/specification)
and uses only its standard frontmatter, so the same directory works in any compliant
agent.

## Skills

| Skill | Use it to |
|---|---|
| [authoring-skills](skills/authoring-skills) | Write or restructure a skill that works across agents |
| [evaluating-skills](skills/evaluating-skills) | Review, benchmark, and tune the triggering of a skill |
| [selecting-technologies](skills/selecting-technologies) | Choose stable, proportionate technologies with current evidence |
| [designing-modules](skills/designing-modules) | Set module boundaries proportional to project size |
| [designing-apis](skills/designing-apis) | Design maintainable, evolvable API contracts |
| [writing-tests](skills/writing-tests) | Write tests that catch regressions and repair flaky suites |
| [debugging-failures](skills/debugging-failures) | Find and fix the root cause of a crash, wrong output, or bug report |
| [writing-typescript](skills/writing-typescript) | Write TypeScript the type checker can hold to account |
| [verifying-changes](skills/verifying-changes) | Prove a change works by running it the way it really runs |
| [creating-verification-harnesses](skills/creating-verification-harnesses) | Give a project a verify skill any agent can follow, and keep it current |
| [checking-invariants](skills/checking-invariants) | Check races, orderings and state machines across every case in a bound (TLA+, enumeration) |
| [measuring-performance](skills/measuring-performance) | Measure before and after any speed or resource claim |
| [fanning-out-work](skills/fanning-out-work) | Split checks across slices or race alternatives, and merge one report you can trust |
| [writing-adrs](skills/writing-adrs) | Record significant decisions and their tradeoffs |
| [reviewing-code](skills/reviewing-code) | Review diffs with evidence and false-positive control |
| [reviewing-designs](skills/reviewing-designs) | Review architecture proposals against the actual project |
| [building-llm-applications](skills/building-llm-applications) | Build reliable, evaluated, cost-bounded LLM features |

### Close calls

| If the request is | Use | Not |
|---|---|---|
| "Rewrite this skill" or "its description never fires, fix it" | authoring-skills | evaluating-skills, which measures whether a skill triggers or helps |
| "Is this PR safe to merge?" | reviewing-code | reviewing-designs, which reviews proposals, ADRs, RFCs, and plans |
| "Postgres or SQLite?" | selecting-technologies | writing-adrs, which records the decision once made; often both apply |
| "Split billing out of orders" | designing-modules | designing-apis, which covers the contract with clients |
| "Add tests for this module" | writing-tests | reviewing-code, which reviews a change and does not add tests |
| "Checkout returns 500, fix it" | debugging-failures | writing-tests alone; it adds the regression test once the cause is known, and both often apply |
| "This test fails randomly on CI" | writing-tests | debugging-failures, which is for failures with an unknown cause in the product code |
| "Tests pass, but does it really work?" | verifying-changes | writing-tests, which adds lasting tests; verifying-changes runs the real thing once |
| "Give agents a standard way to launch and drive the app" | creating-verification-harnesses | verifying-changes, which checks one change; the harness is what it then follows |
| "The orders page got slow" | measuring-performance | debugging-failures, which is for wrong behavior rather than slow behavior |
| "Run every package's checks and give me one report" | fanning-out-work | writing-tests, which writes the tests those checks run |
| "Can two workers ever run the same job?" | checking-invariants | reviewing-designs, which reviews a whole proposal against the project; both apply to a design |

## Install and update

The Git repository is the canonical distribution. Every installable directory under
`skills/` follows the Agent Skills specification and can be copied to any
spec-compliant agent. The generic [`skills`](https://github.com/vercel-labs/skills)
CLI is the recommended installer; Claude Code's marketplace is an optional adapter.

### Recommended: the `skills` CLI

Install every skill into the current project and all supported agent locations:

```bash
npx skills add blxzer77/riff-skills --all
```

Install selected skills or install them for the current user instead:

```bash
npx skills add blxzer77/riff-skills --skill writing-tests --agent '*'
npx skills add blxzer77/riff-skills --all --global
```

Inspect and update an existing installation:

```bash
npx skills list
npx skills check
npx skills update
npx skills update writing-tests
npx skills update --global
```

For reproducible project installs, commit the `skills-lock.json` generated by the
CLI. Review changes from `skills update` like dependency updates. The CLI can
restore a locked installation with `npx skills experimental_install
--frozen-lockfile`; this command is currently experimental, so verify it with
`npx skills --help` when upgrading the CLI.

The CLI was checked against version `1.7.6` on 2026-11-08. Its supported agents
and destination directories can change; use `--agent '*'` rather than hard-coding
one vendor's path when installing broadly.

Releases use `vMAJOR.MINOR.PATCH` Git tags. There is no separate vendor-specific
package to keep in sync; the Git repository and the CLI lock data are the source of
truth.

### Manual installation fallback

If the CLI is unavailable, copy a skill directory to the location used by the
agent. The shared standard locations are:

| Scope | Directory |
|---|---|
| Project | `.agents/skills/<name>/` |
| User | `~/.agents/skills/<name>/` |

The copied directory must retain `SKILL.md` at its root. Agents with a different
standard location may be given the same directory through their own configuration.
Copying or symlinking a local checkout does not provide automatic updates; use the
CLI when updates matter.

### Claude Code marketplace (optional)

Claude Code can also add this repository as a plugin marketplace. Refresh the
marketplace catalog before installing an updated plugin, then update or reinstall
it from the `/plugin` menu:

```
/plugin marketplace add blxzer77/riff-skills
/plugin install riff-skills@riff-skills
/plugin marketplace update riff-skills
```

This is an alternative Claude Code integration, not a prerequisite for using the
skills with other agents.

## Habits that must always hold

A skill only acts while it is loaded. For behavior that should hold in every session,
such as adding a regression test with every bug fix, paste the skill's `AGENTS.md`
snippet (where provided) into your project's `AGENTS.md`.

## Contributing

Read [AGENTS.md](AGENTS.md). In short: start from
`template/SKILL.template.md`, follow `skills/authoring-skills`, keep evals under
`evals/<name>/`, and run `python3 scripts/validate.py --strict` before listing a skill. Use
`skills/evaluating-skills` for behavioral benchmarks when that work is explicitly
resumed; installation and cross-agent compatibility are the release gate.

## License

Apache-2.0. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
