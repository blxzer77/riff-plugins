---
name: evaluating-skills
description: Evaluates Agent Skills with static review, trigger tests and with/without benchmarks, then improves them. Use when testing, benchmarking or reviewing a skill, comparing its versions, tuning its triggering, or asking if it helps or is worth its tokens. Not for writing a new skill (authoring-skills).
license: Apache-2.0
metadata:
  verified-on: "2026-11-16"
---

# Evaluating skills

A skill is worth keeping only if the same agent produces measurably better work
when the skill is actually loaded, and the description routes it to the right tasks.
Do not treat an installed-but-unloaded run as evidence about the skill body. Evaluate
in four layers, cheapest first, and stop at the layer that answers the user's question.

| Layer | Answers | Cost | Guide |
|---|---|---|---|
| 1. Static review | Is it well-formed and well-written? | no agent runs | `references/static-review.md` |
| 2. Trigger evals | Does the agent load it at the right times? | short exploratory runs | `references/trigger-evals.md` |
| 3. Output evals | Does it improve results, at what cost? | paired runs per case | `references/output-evals.md` |
| 4. Comparison | Which of two versions is better overall? | reviewer passes | `references/comparator.md` |

When the user does not name a question, start with layer 1, then choose the
lowest-cost layer that answers the remaining question: layer 2 for discovery,
layer 3 for behavior and value, and layer 4 only for comparing versions. For a
complete assessment, run layers 1, 2, and 3 in that order; add layer 4 only when
two versions need a holistic comparison.

## Workflow

- [ ] Read the skill: `SKILL.md`, its references, and the repository's
      `evals/<skill-name>/` directory if present.
- [ ] Layer 1: run the repository validator if there is one, then review against
      `references/static-review.md`. Fix critical findings before spending runs.
- [ ] Pick the agent(s) and model(s) the skill must serve. Read
      `references/agents.md` for the supported adapters. The scripts run agents
      without permission prompts and do not confine them to the sandbox: run them
      in a container, VM, or confining wrapper. An unconfined agent can read
      anything your user can, including the evals' expected outputs and other
      runs, so it endangers the machine and can contaminate the result. If you
      cannot confine runs, tell the user first, use only trusted fixtures, and
      check transcripts for reads outside the working directory.
- [ ] Ensure `evals/<skill-name>/evals.json` exists (≥ 3 cases). Draft missing cases
      with the user; their real tasks make better cases than invented ones.
- [ ] Layer 2: ensure `evals/<skill-name>/trigger-queries.json` exists, measure,
      optimize if needed. Treat routing and skill-body quality as separate questions. A simple
      task may not invoke a useful skill; that alone is not a description failure.
- [ ] Layer 3: run, grade, aggregate, review with the user, iterate. Prompts must
      not reveal the behavior being tested. Prefer artifact-based assertions, and
      validate each mechanical check against the untouched fixture, a good output,
      a near-miss, an empty output, and a correct alternative implementation.
      Exclude timeouts, API errors, invalid grading, and with-skill runs that did
      not load the skill from the treatment effect; report each count separately.
      If a check or fixture changes, re-grade every existing configuration on the
      same artifacts before interpreting the result. Replace pass-both and
      fail-both assertions; inspect primary-only and baseline-only cases.
- [ ] Report (template below). Leave the workspace for the user; it is not committed.

## Scripts

All scripts are Python 3.11+ standard library; run them, don't read them. Each takes
`--help`. File formats are in `references/schemas.md`.

The adapter names, native skill invocation, treatment status, retries, timeouts, and
sandbox isolation described in the references are this repository's harness policy,
not Agent Skills requirements or universal agent behavior. If a platform lacks an
adapter, isolation, structured logs, or a grading script, use the documented manual
branch and state the limitation.

| Script | Purpose |
|---|---|
| `scripts/run_evals.py` | Run every case with and without the skill in fresh sandboxes |
| `scripts/grade.py` | Grade runs: assertion scripts mechanically, the rest with an LLM grader |
| `scripts/aggregate.py` | Write `benchmark.json` / `benchmark.md` with deltas and assertion patterns |
| `scripts/run_triggers.py` | Measure trigger rates for a query set or a candidate description |
| `scripts/run_routing.py` | Install a whole suite and see which skill each query actually loads |
| `scripts/split_queries.py` | Assign a fixed, stratified train/validation split |

The supporting modules `scripts/agents.py`, `scripts/common.py`, and
`scripts/sandbox.py` are imported by these commands; do not run them directly.

## References

- `references/static-review.md` — read for the static-review rubric.
- `references/trigger-evals.md` — read for trigger-query design and description tuning.
- `references/output-evals.md` — read for output benchmark design and iteration.
- `references/agents.md` — read before choosing an agent adapter or interpreting its logs.
- `references/schemas.md` — read when creating or inspecting eval artifacts.
- `references/grader.md` — read when grading model outputs or reviewing grader feedback.
- `references/analyzer.md` — read when interpreting benchmark patterns.
- `references/comparator.md` — read for a blind comparison of skill versions.

Workspaces default to `.workspace/<skill-name>/` in the current directory. Keep that
path out of version control and away from any directory agents scan for skills.

## Without the scripts

When no supported agent CLI is available, follow the same layout by hand. For each
case and configuration:

1. Copy the case's files into a new, empty directory outside every repository,
   under a neutral name. Agents load instruction files from the working directory
   and its parents, and a workspace path names the case, the configuration and the
   skill.
2. Start a fresh session in that directory, with the skill for one configuration
   and without it for the other. Send the case prompt exactly as written: no role
   preamble, no note about where to work, nothing about evaluation, and no request
   to report which skills were used; read that from the transcript.
3. Save the final response, the transcript, and the diff against the copied files
   under `iteration-N/eval-<name>/<config>/run-1/outputs/`, then grade with
   `references/grader.md`.

A sub-agent keeps a run's context clean only if it can start in that directory;
one that starts in your repository, or has to be told where to work, sees the
repository's instructions or the path. Otherwise use separate sessions. Never grade
a run in the same context that produced it.

## Gotchas

- Instructions leak into runs: user-level instruction files, globally installed
  skills, and the instruction files of any repository the run's directory sits in.
  The scripts start every run outside any repository and the verified adapters
  disable the other two; manual runs must do the same.
- Agents behave differently when they can tell they are being evaluated. Models
  pick out evaluations well above chance, more so in agentic tasks, and often guess
  what is being tested (Needham et al. 2025, arXiv 2505.23836). Keep evaluation
  words (eval, benchmark, baseline, grader, fixture, configuration names) and the
  skill's name out of the path, git history, file names and prompt the agent sees;
  only the installed skill may carry its name.
- Agents skip skills for simple one-step requests. A trigger miss on a trivial query
  says nothing about the description.
- An assertion that passes in both configurations measures the agent, not the skill.
  A high with-skill pass rate built on such assertions is meaningless. Keep the
  raw per-run rate; majority summaries must not hide 2/3 from 3/3.
- A with-skill run that never loads the skill is `not_treated`, not a skill failure;
  measure it as a routing result and exclude it from body-effect comparisons.
- Timeouts, API errors, missing grading, and invalid grader output are infrastructure
  failures. Exclude them from quality denominators and report their counts.
- The grader's verdict rests on artifacts. If the response claims work the diff does
  not show, that is a failure, not a pass on the strength of the claim. Assertions
  need stable IDs; duplicate text must never be used to match verdicts.
- Compare cost with benefit: a skill that adds 2 points of pass rate for double the
  tokens may be worse than no skill.
- Results from one agent or model do not transfer. Report which ones were tested.
- A failed LLM grading is not a failed run. Before acting on a low score, read the
  evidence; "grader output unparseable" means re-grade, not revise the skill.
- When a run with the skill scores lower, read its output before blaming the skill.
  Often the cause is narrow, such as a bundled template the agent applied over the
  project's own conventions, and the fix is one rule with its reason.

## Report

```markdown
## Evaluation: <skill-name> (<agent>, <model>, iteration N)

Static review: pass | needs work | major revision — <top finding>
Output evals: <primary> <pass%> vs <baseline> <pass%> (Δ <+x pts>), Δ tokens <+n>, Δ time <+s>
Triggering: train <a/b>, validation <c/d>; false triggers: <list or none>

Where the skill helps: <assertion patterns, with the instruction responsible>
Where it hurts or is flat: <...>
Next changes: <ranked, each tied to evidence>
Not tested: <agents/models/cases not covered>
```
