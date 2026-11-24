# Evaluation results

> Historical benchmark recorded: 2026-10-30
> Agent/model: Pi default configuration
> Baseline: same prompts without the skill
> Runs: two repetitions per eval case
>
> Current policy (updated 2026-11-16): run new evaluations on `deepseek-flash`
> through a local agent inside a confining bwrap wrapper. That agent was cometix until
> 2026-11-16 and is nyan since then, at the user's request. Compare results only
> within one agent and model, and never directly with the historical Pi run.
>
> Model change (2026-11-02): `deepseek-flash` hit its monthly cap, so runs on that
> day used `claude-haiku-5-5` (same cometix agent, same bwrap sandbox). Later the
> same day `deepseek-flash` recovered and is the evaluation model again. Results on
> different models are not comparable; each section says which model it used, and
> description and body decisions are made on `deepseek-flash`. The proxy later
> returned HTTP 500 `empty response content` for a minimal deepseek request. On
> 2026-11-16 a minimal probe succeeded again; probe before every batch, because the
> local proxy still drops connections at times.

## New skill `reusing-existing-code` (2026-11-24, `pi` 1.6.0 + `deepseek-flash`, confined)

The blinded re-run below left a failure with no skill to fix it: asked to add a case
next to existing ones, the agent copies the repeated block or the other path's
rules. Three of its five cases discriminate; they are this skill's evals, with the
same fixtures and checks plus one that no new `utils` or `common` module appears
(`tests/test_reusing_existing_code_checks.py`). Every run used the `unshare` wrapper,
3 runs per cell; a cell counts runs that passed every assertion of the case.

| Configuration | synonym-helper | fourth-variant | extract-and-share | Mean tokens |
|---|---|---|---|---:|
| no skill | 3/3 | 0/3 | 0/3 | 42k |
| designing-modules installed (loaded in 2 of 9) | 1/1 treated | none treated | 0/1 treated | 50k |
| designing-modules snippet in the system prompt | 3/3 | 0/3 | 0/3 | 46k |
| the rules as a designing-modules section, in the system prompt | 3/3 | 2/3 | 3/3 | 62k |
| the rules as two snippet lines, in the system prompt | 3/3 | 1/3 | 3/3 | 38k |
| reusing-existing-code installed (loaded in 9 of 9) | 3/3 | 3/3 | 3/3 | 58k |

- The rules work when read; where they live decides whether they are read. The
  five reuse prompts loaded designing-modules in 2 of 15 trigger runs and the same
  rules under their own name and description in 15 of 15, so they became a skill
  rather than a designing-modules section.
- Runs that read the rules tidied inside the file (`_export_csv` in
  `app/exporters.py`) or moved the importer's rules into `app/cli_import.py` or a
  new `app/order_import.py`; none added a grab-bag module or changed the existing
  exporters' or importer's output.
- synonym-helper is noisy: the earlier unconfined baseline failed it 0/3, this one
  passed 3/3. Its fixture has five files, so every run reads the helper; the case
  shows whether the agent reuses what it has read, not whether it searches. The
  "search by what it does" rule is not measured.

Triggering, installed alone, 3 runs per query, threshold 0.5:

| Description | Train pos | Train neg | Validation pos | Validation neg |
|---|---:|---:|---:|---:|
| adopted | 6/6 | 2/6 | 4/4 | 2/4 |
| a longer "Not for" list (bugs, flaky tests, API design, edits that add no behavior) | 6/6 | 1/6 | — | — |
| structurally different, leading with the action | 6/6 | 0/6 | — | — |

- Installed alone, the skill loads for most code tasks in its fixtures (a bug fix, a
  speedup, moving a module, API design, type hints), and neither narrower
  description lowered that; they were not run on validation.
- Installed with writing-tests, verifying-changes, designing-modules,
  debugging-failures and reviewing-code (validation set, 1 run per query): its own
  positives 4/4 (always with writing-tests), its own negatives 0/4. It loaded on
  three other skills' queries, each time with the owner also loaded: a gradual
  storage replacement, a new webhook event type, and a REST API design request (the
  one clear false trigger). The other skills' owner-load counts match the earlier
  five-skill run (debugging-failures 2/4, verifying-changes 2/6, writing-tests 2/4).
- Eight queries written after the choice: installed alone 7/8 (positives 12/12
  runs; a request to find why an export writes its byte-order mark twice loaded
  it in 2 of 3); with the five neighbors, 3 runs each, its positives loaded it in
  11/12 runs and its negatives in 0/12.
- Not tested: other agents and models, the full suite installed at once, and a
  fixture large enough that the agent must search for the existing rule.

## `verifying-changes` description for someone else's fix (2026-11-24, `pi` 1.6.0 + `deepseek-flash`, confined)

Under the old description the `fix-claim-that-isnt` prompt loaded the skill in 3 of
15 runs (0/6 trigger runs, 3/9 output runs). The adopted description adds "when
someone says a fix is done" and narrows "reviewing someone else's diff" to "reading
a diff for bugs" (298 characters). Ten trigger queries were added (30 in all,
15/15): four where someone else claims a fix or feature works, four near-misses
(review, debug, regression test, review comments), and two on the ledger fixture.

| Description | Train pos | Train neg | Validation pos | Validation neg | Total | `fix-claim-that-isnt` prompt loads |
|---|---:|---:|---:|---:|---:|---:|
| old | 7/9 | 6/9 | 2/6 | 3/6 | 18/30 | 3/15 |
| adopted | 8/9 | 7/9 | 4/6 | 2/6 | 21/30 | 4/9 |
| alternative ("when told someone else's fix or feature is done") | 7/9 | 6/8 | 3/6 | 3/6 | 19/29 | 4/6 (trigger runs only) |

- Installed alone, 3 runs per query, threshold 0.5. One negative timed out in
  every run of the alternative.
- Installed with reviewing-code, debugging-failures, writing-tests and
  creating-verification-harnesses (validation set, 1 run per query): neither
  description took another skill's queries. The old one was also loaded on three
  harness-building queries (adopted: one) and on one harness negative. The false
  triggers seen with the skill alone (CI setup, a flaky test, a regression test,
  review comments) went to their own skills or to none.
- Six queries written after the choice: 5/6 for both descriptions; both load on
  "profile it" when installed alone.
- The one treated `fix-claim-that-isnt` run with the adopted description passed
  all four assertions, including the reporter's file on both sides; the other two
  runs did not load the skill.

## `verifying-changes`: someone else's fix, checked on both sides (2026-11-24, `pi` 1.6.0 + `deepseek-flash`, confined)

New case `fix-claim-that-isnt`, from pstack's Benny automation (verify-existing-fix).
Another agent says ticket 57 is fixed on a branch and that a cleaned-up copy of the
statement imports. The reporter's original file (byte-order mark and Windows line
endings) still imports 0 transactions on the branch, and the cleaned copy imports
on main too. Every run used an `unshare` mount and PID namespace (agents
reference). The "body in the system prompt" rows append the skill body to bypass
routing, an upper bound on what the text does when read.

| Configuration (3 runs each) | ticket left open | verdict: insufficient | reporter's file on main and branch | other agent's check called non-evidence |
|---|---|---|---|---|
| no skill | 3/3 | 3/3 | 1/3 | 2/3 |
| skill before this change, loaded | 3/3 | 3/3 | 1/3 | 3/3 |
| old body in the system prompt | 3/3 | 3/3 | 2/3 | 3/3 |
| new body in the system prompt | 3/3 | 3/3 | 3/3 | 3/3 |

- The baseline already reaches the right verdict. The gap is the run on the old
  code, which the new "Run the same check on both sides" rule closes when it is
  read (n=3, a weak signal).
- Routing is the larger gap: in 9 with-skill runs of this case the skill loaded 3
  times (0 of 3 with the new text). The description excluded reviewing someone
  else's diff; see the description section above for the change.
- Regression check on the five earlier cases, 1 run each with the new and the old
  text: every assertion passes in both; mean tokens 76k vs 61k.
- Not measured: the UI half of the rule (the evidence shows the final state, not a
  loading screen).

## Reuse over copying, blinded (2026-11-24, `pi` 1.6.0 + `deepseek-flash`)

The 2026-11-23 necessity check for an `evolving-existing-code` skill (6 runs; 4 of 5
scenarios passed, so no skill was added and `template/global-prompt.md` got three
reuse rules in 3f5ed39) was not blinded. Each candidate worked under
`.workspace/evolving-existing-code/iteration-1/eval-<case>/without_skill/`, was told
"Act as the implementation sub-agent", and loaded this repository's `AGENTS.md` and
the user's global prompt. This re-run uses the harness after 8206c5c, with the same
five fixtures (rebuilt from the thread's file diffs) and task text and 3 runs per
cell. Its mechanical checks were validated against the untouched fixture, two
correct solutions written differently, and copy-paste near-misses.

| Case (the reuse it needs) | bare | template before 3f5ed39 | template at 3f5ed39 |
|---|---|---|---|
| synonym-helper: call the slug helper in another module | 0/3 | 2/3 | 3/3 |
| fourth-variant: tidy three exporter copies before adding a fourth | 0/3 | 0/3 | 2/3 |
| extract-and-share: share the CLI importer's row rules | 0/3 | 0/3 | 2/3 |
| second-lane-wiring: alert through the existing dispatch | 3/3 | 3/3 | 3/3 |
| replace-legacy-path: replace the flat rate in place | 3/3 | 3/3 | 3/3 |

"Template" runs appended the template's Communication through Verification
sections to the system prompt; only the three Working method lines differ. Behavior
checks passed in all runs; mean tokens 57k / 53k / 55k.

- Blinded, the bare model failed all 9 runs on the three cases that need finding
  or tidying existing code. The unblinded round passed extract-and-share, so its
  conclusion that the baseline mostly reuses does not hold.
- The 3f5ed39 rules help (tidy-first cases 0/6 to 4/6, helper reuse 2/3 to 3/3) but
  do not settle it, and they reach only agents that load the global prompt.
- Runs were unconfined (no bwrap on this machine), against the policy above. One
  run (template before 3f5ed39, synonym-helper) searched `/root` and `/tmp`, read
  the case's expected output, and queried the orchestrating app's database; it was
  discarded and the case re-run under an `unshare` mount and PID namespace. A
  transcript scan found no other run reading outside its directory.
- Not tested: other agents and models, and any with-skill configuration. The
  workspace (fixtures, checks, check validation, wrappers) is
  `.workspace/evolving-existing-code/`, not committed. The three discriminating
  cases became `reusing-existing-code` (section above).

## New skill `creating-verification-harnesses` (2026-11-17, Claude Haiku 5.5 subagents)

From pstack's create- and maintain-verification-skill: build a project-local verify
skill (Launch, Doctor, Drive, Evidence, Cleanup, a feature map), prove it once, and
keep it current. Same method as the section below: fresh Haiku subagents per run,
three runs per configuration, the with-skill run told to read `SKILL.md`, judged
assertions graded blind by Sonnet subagents (`tests/test_creating_verification_harnesses_checks.py`
covers the checks). Runs that start the notes server ran at most two at a time, and
each run was graded for leftover servers as soon as it finished, so runs could not
reuse each other's servers or ports.

| Case | With skill | Without skill |
|---|---:|---:|
| create-harness (notes service; README's default data dir is the team's real notes) | 1.00 | 0.67 |
| stale-harness (existing verify skill written for 1.x; app now uses `new` and `/healthz`) | 1.00 | 1.00 |
| cli-harness (short-lived CLI; default data file is the team's real list) | 1.00 | 0.78 |
| **Mean** | **1.00** | **0.81** |

- No run in either configuration touched the real data or left a server running,
  and every stale-harness run fixed only the skill and reran it live. Haiku already
  isolates by default here.
- With the skill, 3/3 wrote instructions that give the launch, health check,
  driving, evidence and cleanup steps; without it, 0/3 did: each wrote a single
  script that does all of that internally and documented only the command to run
  it. That is a difference in form as much as in quality, since a self-contained
  script is also usable by an agent; read the 0.67 with that in mind.
- In the CLI case, 3/3 with the skill kept the run's output as an evidence file;
  without it, 1/3 did (the others only printed it).
- The stale-harness check first counted prose notes such as "`/health` returns 404
  since 2.0" as stale commands; it now reads code blocks and command-like inline
  code, skips migration notes, and has tests for both.

Triggering, judged from descriptions by three Haiku subagents (all 17
descriptions, the skill's 20 queries shuffled and unlabeled): 20/20 (train 6/6 and
6/6, validation 4/4 and 4/4).

## `checking-invariants`, `fanning-out-work`, and `verifying-changes` again (2026-11-17, Claude Haiku 5.5 subagents)

From pstack's verification and swarm material: two new skills (`checking-invariants`
for model checking and exhaustive exploration, `fanning-out-work` for slices and
races) and an extended `verifying-changes` (what counts as evidence; make sure the
thing you run is the thing you changed). Fixtures, checks and tests for the checks
first (`tests/test_checking_invariants_checks.py`, `tests/test_fanning_out_work_checks.py`,
new cases in `tests/test_verifying_changes_checks.py`).

**Why not nyan.** The first nyan batch (verifying-changes, 30 runs) and the
baselines for the two new skills hit the local model proxy's connection errors in
more than half of the runs, mostly in runs longer than three minutes; retries and
top-ups did not recover. At the user's request the comparisons were rerun with
Claude Haiku 5.5 subagents. These numbers are not comparable with the nyan or Pi
sections.

Method, and how it differs from the harness:

- Each run is a fresh Haiku subagent in its own copy of the fixture on nyan-pc, not
  allowed to start subagents. The with-skill run is told to read the skill's
  `SKILL.md` first; loading by description is not tested here.
- Assertions about tool calls are judged from the agent's own command list and the
  diff it left, not from a transcript.
- Script assertions ran as usual. Judged assertions were graded by Sonnet 5.5
  subagents on copies under random labels, without the configuration; responses
  that follow the skill's report format can still hint at it.
- Both configurations were told where `tla2tools.jar` is, which may nudge either
  toward model checking.
- Three runs per configuration for the new skills, two for `verifying-changes`.

| Case | With skill | Without skill |
|---|---:|---:|
| invariants: event-sequences (order workflow; a 5-event path breaks a finance rule) | 0.89 | 0.67 |
| invariants: design-only-protocol (can a lease design let two workers run a job?) | 1.00 | 1.00 |
| invariants: red-model-check (TLC fails after a cancel button; fix the code, keep the property) | 1.00 | 1.00 |
| **checking-invariants mean** | **0.96** | **0.89** |
| fan-out: package-sweep (six check.sh; one prints OK and exits 1, one cannot run) | 1.00 | 0.50 |
| fan-out: patch-queue (four patches; two touch the same lines) | 1.00 | 1.00 |
| fan-out: slug-race (pick the fastest correct of three) | 0.83 | 0.67 |
| **fanning-out-work mean** | **0.94** | **0.72** |
| verifying-changes, all five cases | 1.00 | 1.00 |

- `checking-invariants`: the difference is in the fix, not the analysis. With the
  skill, 2 of 3 runs left no event sequence up to depth 6 that breaks a rule while
  keeping the reorder flow; without it, 0 of 3. Both configurations explored
  sequences systematically, found the lease race (several with TLC), and kept the
  invariant in the red model check instead of weakening it.
- `fanning-out-work`: with the skill, 3/3 reported the uncheckable package as
  blocked rather than failed (1/3 without), and 2/3 timed every candidate the same
  way before picking (1/3 without). Every run judged each patch on a clean copy.
- `verifying-changes`: Haiku already does what the new body asks: it rebuilt the
  bundle and ran `bin/greet`, inspected git state after the dry run, and said the
  real report store was untested, with or without the skill. The extension is kept
  on the strength of the earlier deepseek-flash gaps, but it shows no effect on
  Haiku. The interrupted nyan iteration 3 is not used: too many runs are missing,
  and its `stale-bundle` check had a defect (below).
- Defects found in the new checks while grading, fixed before the numbers above:
  the `stale-bundle` check demanded `O'Neil` for `o'neil`, which the prompt never
  asked for; the fan-out report parser read a verdict from summary sentences
  ("3 pass (auth, ...), 2 fail") and from words like "clean" before reading table
  rows, and missed "not safe"; the unchanged-tree check missed added files. Each
  fix has a test.

Triggering, judged from descriptions by three Haiku subagents (all 16 skill
descriptions, 40 shuffled unlabeled queries; a query counts as triggered when at
least two of three judges load the owner):

| Skill / description | Train pos | Train neg | Validation pos | Validation neg | Total |
|---|---:|---:|---:|---:|---:|
| checking-invariants, first | 5/6 | 6/6 | 3/4 | 4/4 | 18/20 |
| checking-invariants, adopted ("or a model check fails") | 6/6 | 6/6 | 3/4 | 4/4 | 19/20 |
| fanning-out-work | 6/6 | 6/6 | 3/4 | 4/4 | 19/20 |

The remaining misses go to neighbours that also fit: "fuzz the duration parser"
to writing-tests, and "compare two rate limiter implementations" to
measuring-performance. This is a judgment from descriptions, not an agent run with
installed skills.

Runs, blind copies and grades: the session scratch folder (`haiku/`, `blind/`,
`grades/`, `trigger-judge/`); not kept in the repository.

## New skill `verifying-changes` (2026-11-16, `nyan` + `deepseek-flash`)

Built evals first like the other new skills (`tests/test_verifying_changes_checks.py`;
practices from pstack's prove-it-works, checked against the Claude Code best
practices). Three runs per configuration, four at a time.

| Case | Adopted description | First description | Without skill |
|---|---:|---:|---:|
| default-comes-from-config (shipped config overrides the code default) | 1.00 (3/3 loaded) | 1.00 (1/3 loaded) | 1.00 |
| second-copy-of-a-setting (middleware keeps its own 15-minute limit) | 1.00 (3/3) | 1.00 (3/3) | 0.83 |
| cannot-run-the-real-thing (retries; the real store is production only) | 1.00 (2/3) | 1.00 (1/3) | 0.67 |
| **Mean** | **1.00** | **1.00** | **0.83** |

- Every run in every configuration made the mechanical checks pass. The gain is in
  the report: no baseline run told the user the retries were never tried against
  the real report store (0/3), and one baseline run never checked a session idle
  beyond 15 minutes.
- The first description ("Use when finishing a feature, fix or config change,
  before saying it works…") was loaded in only 5 of 9 with-skill runs: the
  prompts ask for a change, not for verification. The adopted one says "Use when
  implementing a feature, fix, default or config change and before saying it
  works…" and was loaded in 8 of 9 (iteration 2, with-skill only, compared with
  the iteration-1 baseline). Scores are over loaded runs.
- `default-comes-from-config` passes without the skill and should be made harder.
- Cost: about 0.44M vs 0.38M tokens per run; time about equal.

Triggering (installed alone, 3 runs per query, threshold 0.5, all 20 queries):

| Description | Train pos | Train neg | Validation pos | Validation neg | Total |
|---|---:|---:|---:|---:|---:|
| first | 5/6 | 6/6 | 3/4 | 4/4 | 18/20 |
| adopted | 6/6 | 6/6 | 2/4 | 4/4 | 18/20 |

The adopted description fixes the train miss ("double-check the generated invoice
really uses the new template") but "the feature flag is on, confirm users actually
get the new flow" fell from 2/3 to 1/3, and "did the switch to the new payments
client actually take effect?" stays at 0/3. It was chosen for loading during real
change requests, which the trigger set does not contain.

Results: `.workspace/verifying-changes/iteration-1/` (baseline and first
description), `iteration-2/` (adopted description), `triggers/`.

## New skill `measuring-performance` (2026-11-16, `nyan` + `deepseek-flash`)

Built the same way as `debugging-failures` (from pstack's benchmark checklist,
checked against Brendan Gregg's active benchmarking and the Python profiler docs):
fixtures and checks first (`tests/test_measuring_performance_checks.py`), a
baseline against a placeholder skill, then the body. Three runs per configuration,
four at a time; all nine with-skill runs loaded the skill.

| Case | With skill | Without skill |
|---|---:|---:|
| wrong-suspect (user blames json.dumps; cost is a linear customer scan) | 1.00 | 1.00 |
| faster-but-different (dedupe_fast is faster but loses order callers need) | 1.00 | 0.67 |
| noise-not-regression (a 12% alert after a variable rename) | 1.00 | 1.00 |
| **Mean** | **1.00** | **0.89** |

- Without the skill, deepseek-flash already profiled before optimizing, kept the
  export output identical (all runs at least 10x faster), and called the 12% alert
  noise after rerunning the benchmark. Those cases do not discriminate and should
  be made harder.
- The gain is in comparing implementations: no baseline run timed both functions
  with repeated runs on more than one input size (one timed nothing, one used a
  single size, one only checked ordering). With the skill, 3/3 did. Every run in
  both configurations noticed the lost ordering and kept the callers on `dedupe`.
- Cost: 0.49M vs 0.51M tokens and 64 s vs 104 s per run; the baseline spent longer
  on the noise case (272 s vs 122 s).

Results: `.workspace/measuring-performance/iteration-1/`.

Triggering (installed alone, 3 runs per query, threshold 0.5, all 20 queries):
17/20, no false positives, all train queries pass. The validation query "someone
rewrote send.go and says it's 5x faster, check that" triggers 1/3. Two runs ended
in agent errors and are not counted, so two queries rest on two runs. The
description was kept. Results: `.workspace/measuring-performance/triggers/`.

## New skills `debugging-failures` and `writing-typescript` (2026-11-16, `nyan` + `deepseek-flash`)

Both skills come from reading pstack (`cursor/plugins` `bf0c7cd`, MIT) and were built
evals first: fixtures, mechanical checks, and tests for the checks
(`tests/test_debugging_failures_checks.py`, `tests/test_writing_typescript_checks.py`)
before any body. Three runs per configuration, four agents at a time, 900 s timeout.
The baseline ran before the bodies existed, against a placeholder skill directory
with `--configs without_skill`; the with-skill runs were added to the same
iteration later.

TypeScript fixtures need node and tsc inside the sandbox. `nyan-sandboxed` now takes
two optional read-only binds, `RIFF_SANDBOX_NODE_DIR` (node 24.21.0) and
`RIFF_SANDBOX_TYPESCRIPT_DIR` (an installed TypeScript 5.9.3), and puts them on the
sandbox `PATH`; without them nothing changes. Nothing was installed. The checks
also pass on TypeScript 7.0.2.

| Case | With skill | Without skill |
|---|---:|---:|
| debugging: misleading-hypothesis (user blames encoding; cause is quoted commas) | 1.00 | 0.89 |
| debugging: retry-scope (retry transient gateway errors only) | 1.00 | 0.67 |
| debugging: symptom-at-the-caller (mutable default; a second caller is affected) | 1.00 | 0.67 |
| **debugging mean** | **1.00** | **0.74** |
| typescript: config-boundary (reject a malformed config at load) | 1.00 | 0.89 |
| typescript: union-member-added (new event kind; switches with fallbacks) | 1.00 | 0.00 |
| typescript: absent-value (lastSeen for users with no sessions) | 1.00 | 1.00 |
| typescript: same-typed-arguments (swapped recipient must not compile) | 1.00 | 1.00 |
| **typescript mean** | **1.00** | **0.72** |

- Debugging: every baseline run fixed the bug (all mechanical checks pass in both
  configurations). The skill changed the process and the report. Without it, no
  `retry-scope` run reproduced the failure before editing `charge.py` (0/3), and no
  `symptom-at-the-caller` run told the user that the dashboard caller was affected
  (0/3). With it, 3/3 and 3/3.
- TypeScript: without the skill, every `union-member-added` run added the new case
  and kept the `default` fallbacks, so a further event kind still compiles and
  renders "Unknown activity" (0/3 on the mutation check). With the skill, 3/3 made
  both switches exhaustive. One `config-boundary` baseline asserted the log level
  into its union type (`as LogLevel`) after a string check.
- `absent-value` and `same-typed-arguments` pass in both configurations and should be
  replaced by harder cases. Several judged assertions in the debugging cases also
  pass in both.
- One with-skill run (`misleading-hypothesis` run-2) did not load the skill. It is
  excluded, so that case's with-skill score comes from two runs. Grading was
  otherwise valid; there were no API errors or timeouts.
- Cost: debugging 0.58M vs 0.34M tokens and 39 s vs 22 s per run; TypeScript 0.50M
  vs 0.36M tokens and 37 s vs 25 s.
- Before switching to nyan, one run per case without the skill was done by Claude
  subagents in this session (model not recorded, not comparable). They also passed
  every debugging check, and failed only `union-member-added` among the TypeScript
  cases.

Results: `.workspace/debugging-failures/iteration-1/`, `.workspace/writing-typescript/iteration-1/`.

Triggering, each skill installed alone, 3 runs per query, threshold 0.5, 600 s
timeout, all 20 queries:

| Skill / description | Train pos | Train neg | Validation pos | Validation neg | Total |
|---|---:|---:|---:|---:|---:|
| debugging-failures | 6/6 | 6/6 | 4/4 | 4/4 | 20/20 |
| writing-typescript, first description | 4/6 | 6/6 | 2/4 | 4/4 | 16/20 |
| writing-typescript, adopted description | 6/6 | 6/6 | 3/4 | 3/4 | 18/20 |

- The first TypeScript description listed mechanics (parsing outside data, union
  members, maybe-missing values) and missed "type this `any` fetch result" and
  "port this package to TypeScript". The adopted one names those situations and
  "writing or changing TypeScript types". It was revised on the train failures only.
- Still open on validation: "the switch has a default that hides new statuses"
  triggers 1/3 (0/3 before), and "OrderList.tsx is slow with 10k rows" now triggers
  2/3, a false positive.
- Results: `.workspace/{debugging-failures,writing-typescript}/triggers/`.

## `reviewing-designs` on deepseek-flash (2026-11-16, `nyan` + `deepseek-flash`)

The 2026-11-02 redesign was measured only on haiku. This repeats it on the evaluation
model with the current body (which since today also covers designs reviewed without
access to the project; the fixtures always include one, so that branch is not
exercised). Four cases, three runs per configuration, four runs at a time. Every
with-skill run loaded the skill; there were no API errors and no invalid grading.

| Case | With skill | Without skill |
|---|---:|---:|
| donor-report (query bypasses module APIs) | 1.00 | 1.00 |
| pickup-reminders (sound design, accepted trade-off) | 1.00 | 0.83 |
| stock-import (insert violates a CHECK constraint) | 1.00 | 1.00 |
| stock-search (sound design, small catalogue) | 1.00 | 0.89 |
| **Mean** | **1.00** | **0.93** |

- All three failed baseline assertions are the same one: the design is sound, but
  the review withholds approval over details an implementer settles while building
  (pickup-reminders 1/3 approved, stock-search 2/3). With the skill, 6/6 approved.
- Finding the planted defects is not the gain: both configurations found them in
  every run, as on haiku. Most assertions pass in both and should be replaced by
  harder cases.
- Cost: 1.20M vs 0.81M tokens per run. Time is 436 s vs 100 s on average, inflated
  by pickup-reminders: 3 of its 6 with-skill attempts hit the 900 s timeout and were
  retried, so its with-skill scores come from the runs that finished. The harness
  retried timeouts at the time; it no longer does.

Results: `.workspace/reviewing-designs/iteration-3/`.

## Suite routing judged by Claude subagents (2026-11-16)

`run_triggers.py` installs one skill at a time, so it cannot show one skill taking
another's queries. A full `run_routing.py` run with nyan was stopped at 20 of 196
runs, and the user asked for subagents instead. Method: eight Claude subagents in
this session (model not recorded), each given the ten current descriptions and
24–25 shuffled queries from all trigger sets, without owner or label, with no
tools, asked which skills they would load before starting each request. This is a
judgment from descriptions alone, not an agent run with installed skills, and each
query was judged once.

| Skill | Positives, owner chosen | Negatives, owner chosen |
|---|---:|---:|
| authoring-skills | 9/9 | 2/9 |
| building-llm-applications | 10/10 | 0/10 |
| designing-apis | 10/10 | 0/10 |
| designing-modules | 10/10 | 0/10 |
| evaluating-skills | 9/9 | 0/9 |
| reviewing-code | 10/10 | 0/10 |
| reviewing-designs | 10/10 | 0/10 |
| selecting-technologies | 8/10 | 0/10 |
| writing-adrs | 8/10 | 0/10 |
| writing-tests | 9/10 | 0/10 |
| **Total** | **93/98** | **2/98** |

- All five misses are indirect triggers that the descriptions spell out ("even if
  told only to add or set up something", "even if nobody mentions ADRs", "even if
  tests aren't mentioned"). Two `selecting-technologies` queries ("upgrade whatever
  is outdated", "add a Dockerfile") chose nothing; two implicit `writing-adrs`
  decisions went to `building-llm-applications` + `selecting-technologies` and to
  `designing-modules`; one feature task with tests went to `designing-apis` alone.
- Both false choices are `authoring-skills` on `evaluating-skills` territory
  (optimizing a description's trigger rate; why an agent did not load a skill),
  each chosen together with `evaluating-skills`. The two descriptions overlap on
  description tuning.
- 16 positives also chose a second skill, mostly expected pairs: a module split
  with an ADR, a design review with module boundaries, an API change with tests.

Results: `.workspace/_suite/routing/20261116-subagent-judgment-all.json`.

## `designing-apis` with a fixture and mechanical checks (2026-11-16, `nyan` + `deepseek-flash`)

Until now every `designing-apis` assertion was graded by an LLM on prose, without a
fixture. Cases 1 and 2 now run in `files/shop-api`, a contract-first API repository
(`openapi.json`, conventions, a contract check), and ask for the change in the
contract. Five scripts in `evals/designing-apis/checks/` grade the result. Each check
was validated on the untouched fixture, two good solutions written differently, and
near misses (`tests/test_designing_apis_checks.py`, 18 tests, run in CI). Case 3
(streaming and webhooks) is unchanged. Three runs per configuration, four at a time.
All runs completed, every with-skill run loaded the skill, and grading was valid.

| Case | With skill | Without skill |
|---|---:|---:|
| design-retryable-export | 0.87 | 0.87 |
| evolve-search-list | 1.00 | 1.00 |
| ai-stream-and-webhook | 1.00 | 1.00 |
| **Mean** | **0.96** | **0.96** |

- No measured difference. Without the skill, deepseek-flash already started exports
  as an operation resource with defined states and a download link, required an
  `Idempotency-Key`, kept `GET /items` unchanged for old clients (adding `/v2/items`
  or optional parameters), and paged with a cursor and a bounded limit. Spot checks
  of baseline contracts confirm the checks are not lenient.
- The one assertion that fails in both (2 of 3 runs each) asks the contract to say
  what happens when a retry reuses a key with a different body, or after the key
  expires.
- Cost: 0.56M vs 0.34M tokens per run.
- The earlier positive result for this skill (retryable export, 1.00 vs 0.33,
  2026-10-31) came from a prose-only case graded by an LLM. On artifacts in a real
  repository, its value on this model is not shown; harder cases, or a decision to
  trim the skill, are open.

Results: `.workspace/designing-apis/iteration-4/`.

## Description length cap (2026-11-16, `nyan` + `deepseek-flash`)

All ten descriptions were cut to at most 300 characters (they were 398–607), and
`scripts/validate.py` now rejects longer ones. Old and new descriptions were run on
each skill's validation queries: 3 runs per query, threshold 0.5, 600 s timeout.

Setup, at the user's request:

- Agent: local `nyan` 0.2.1 through the `claude-code` adapter, wrapped by
  `~/.cache/riff-skills/bin/nyan-sandboxed`, with its own home in
  `~/.cache/riff-skills/nyan-home`. The wrapper is bwrap, like
  `cometix-sandboxed`. It copies `.claude/skills` into `.nyan/skills`, because nyan
  discovers skills only there. It also passes `--settings`, because
  `--setting-sources project` drops nyan's model profiles. These results are not
  comparable with cometix runs.
- The old and new descriptions of a skill ran at the same time, with 4 agents in
  total. Twelve or more concurrent agents hit `429 rate_limit_error`. Between about
  03:00 and 06:00 local time, the local model proxy also returned intermittent
  connection errors. Runs touched by either were discarded and re-run. The kept
  results have no API failures, and their remaining errors are 600 s timeouts.

| Skill | Length old → new | Old passed | New passed | Notes |
|---|---:|---:|---:|---|
| authoring-skills | 405 → 297 | 7/8 | 8/8 | `.claude/commands/deploy.md` conversion went from 0/3 to 2/3. An earlier new-only run scored 0/3, so this is within noise. |
| building-llm-applications | 575 → 291 | 8/8 | 7/8 | The negative "cheapest per-token pricing" query timed out 3/3 in the new run (old 0/3). It was not misrouted. |
| designing-apis | 456 → 291 | 7/7 | 7/7 | The new description triggered 1/3 on "set up a message broker cluster", below the threshold. |
| designing-modules | 558 → 297 | 8/8 | 8/8 | |
| evaluating-skills | 398 → 299 | 5/8 | 7/8 | "review this pull request for bugs" timed out 3/3 in both. |
| reviewing-code | 607 → 298 | 8/8 | 8/8 | |
| reviewing-designs | 445 → 287 | 8/8 | 8/8 | |
| selecting-technologies | 555 → 296 | 8/8 | 8/8 | |
| writing-adrs | 463 → 299 | 6/8 | 7/8 | |
| writing-tests | 446 → 298 | 6/8 | 6/8 | Flaky-test 1/3 → 0/3; the retry wrapper is 1/3 in both. |
| **Total** | | **71/79** (7 FN, 0 FP) | **74/79** (3 FN, 0 FP) | |

No regression is visible. With 7–8 queries and 3 runs each, the gains are within
run-to-run noise: the same new `authoring-skills` description scored 7/8 and 8/8 in
two runs. Results are the `*-validation.json` files under
`.workspace/<skill>/triggers/` whose UTC timestamps fall between 2026-11-15T16:39Z
and 22:16Z, which is 2026-11-16 in local time.

## `reviewing-designs` redesign (2026-11-02, `claude-haiku-5-5`)

The body was rewritten from the Anthropic review designs listed in its
`references/sources.md` (architecture-critic, code-review, code-reviewer agents,
scan-verifier, and Claude Code's explore-then-plan and adversarial-review
guidance). Changes:

- Read the project before trusting the proposal.
- Check each claim the design depends on against repository files.
- Try to refute a finding before reporting it.
- Keep a design-specific false-positive list: taste, preferred technology,
  speculative scale, re-arguing accepted ADRs, and accepted trade-offs.
- Derive one verdict from severity.

The 80/100 confidence threshold comes from Anthropic's code reviewers. Applying it
to designs is this project's choice. The section checklist, the "require an
alternative" gate, and the confidence-to-severity bands had no source and were
dropped.

The old three cases had no fixture and named the defect in the prompt. The new
cases share one small project, and no prompt names the issue:

| Case | Hidden fact | Expected |
|---|---|---|
| donor-report | the query bypasses module APIs, contradicting accepted ADR 0002 | not approve, cites the ADR or APIs |
| stock-import | `kind = 'import'` violates the `CHECK` constraint in `app/schema.sql` | not approve, cites the constraint |
| pickup-reminders | sound design with a stated, accepted trade-off | approve |
| stock-search | sound design, small catalogue | approve |

Two further cases (a field rename and remember-me login) were dropped because the
baseline passed them completely in the pilot.

Final paired run, 3 runs each, 12/12 with-skill runs treated:

- Pass rate: 0.98 with the skill, 0.83 without.
- Both configurations found both hidden defects in 6/6 runs.
- The difference is all in sound designs: with the skill, 5/6 runs approved;
  without it, 0/6. The baseline withheld approval over things the proposals had
  already settled.
- The one with-skill miss is defensible: the crontab has no `MAILTO`, so the
  proposal's alerting claim is unverified.

Cost: about +585k tokens and +133 s per run.

Check fixes were applied before the final run, with the earlier runs re-graded:

- `fact_cited` patterns were tightened after bare path mentions passed.
- A decoy assertion had counted real query bugs as decoys.
- Gaps in the sound-design fixtures were closed: LIKE escaping, the retry bound,
  and the subject wording.
- The verdict assertion is now keyed to the stated conclusion, not to headings.

Decision: retain. Its measured value is calibration: it stops the reviewer from
blocking sound designs. Finding defects is not the gain; haiku found them alone.

## `selecting-technologies` redesign (2026-11-02)

Anthropic publishes no technology-selection method. The skill now follows four
principles from Anthropic's plugins and docs (read the existing stack first, check
current versions at run time, simplest option first, skepticism toward the new)
and takes its concrete criteria from OpenSSF, the Node.js release policy,
endoflife.date, and OSV (see its `references/sources.md`). The old weighted
scorecard and trend template had no source and were dropped.

The old cases were pass-both because their prompts named the constraints. The new
fixture cases name none of them; a correct answer depends on facts that changed
after common training data, or on constraints written only in repository files:

| Case | What decides it | Mechanical check |
|---|---|---|
| password-hashing | passlib's last release is 2020-10-08 and it fails at hash time with bcrypt 5.0 | added deps released within 3 years; clean install gives salted slow hashes that verify |
| container-node | Node 18 and 20 are end of life; `engines` says `>=18` | every Node base image on Active/Maintenance LTS |
| claude-summary | many remembered Claude IDs are retired or deprecated | every model ID active on the official deprecations page; tests pass offline |
| background-email | compose and README: one VM, only Postgres backed up, nobody on call | no new broker or stateful service; mail off the request path; tests pass |
| reuse-http (decoy) | httpx already in use | no new dependency or decision document; function works with the given client |

Ageing facts are read from dated snapshots under
`evals/selecting-technologies/checks/data/` so a grade
does not change with the day it runs. Tests and probes run in a network-less
namespace, so a test that calls a live API fails. Each check was validated on
hand-written good solutions (including the standard library's scrypt and PBKDF2,
Postgres job tables, in-process executors, ARG-templated and distroless images,
model aliases and Bedrock IDs) and near-misses (salted SHA-256, passlib with an
old bcrypt pinned, Celery with Redis, `node:latest`, invented model IDs), and
through `grade.py` end to end.

One leakage risk is known: the SKILL.md gotcha that a manifest version floor is
not a deployment target applies directly to container-node. It is a general rule,
so it stays; read a container-node gain with that in mind.

### Baseline pilot on `claude-haiku-5-5`

Two baseline runs per case. All five cases above are pass-both candidates: the
baseline chose argon2-cffi, `node:22-alpine`, `claude-sonnet-4-6`, and an
in-process thread pool, and reused httpx. Haiku's training cutoff (June 2026) is
later than the facts these cases test, so "check instead of remembering" has
nothing to correct. The reuse-http baseline first scored 0.50 because the check
assumed one response shape the prompt never specified; the check now accepts any
plausible shape, and both runs were re-graded on the same artifacts.

A sixth case targets a fact that changed after that cutoff. The repository already
pins `claude-sonnet-4-5-20250929`, deprecated on 2026-09-30 and retiring on
2026-11-30, and the prompt asks for a new feature "using the existing LLM setup".
The baseline kept the deprecated model and did not mention it in 3 of 3 runs.
All three with-skill runs were `not_treated`: the agent listed the installed
`SKILL.md` but did not load it. The description's exclusion ("code changes that
use only what the project already depends on") matches this prompt. That is a
routing result, not evidence about the body; the trigger eval decides whether the
description changes.

### Trigger evaluation on `claude-haiku-5-5`

20 fixture-backed queries, 3 runs each: 19/20, with train 11/12, validation 8/8,
no false positives, and no infrastructure errors. The one train miss, "upgrade
whatever is outdated in requirements.txt", turned out to be a fixture fault. That
fixture's requirements.txt is empty, so the agent correctly found nothing to
upgrade. The query now runs against background-email, whose pins are behind
current releases.

Rerun on that fixture, the current description triggered 3 of 4 completed runs
and a candidate that names upgrades triggered 4 of 4. The difference is within
noise, and the candidate was no better on the rest of train (11/12, three
positives down to 2/3). The description is unchanged.

Decision so far: the body's value is unmeasured on haiku. Five cases are
pass-both. The sixth discriminates on the baseline, but routing does not load the
skill for a prompt that only extends existing code. Forcing the load would no
longer measure the skill as shipped. For "check what is already pinned", the
always-on channel is `assets/agents-snippet.md`, not the skill.

### Deepseek-flash baseline and follow-up case (2026-11-02)

The six-case baseline pilot on deepseek differs from haiku: password-hashing,
container-node, claude-summary, background-email, and reuse-http are still
pass-both; model-in-repo is 1/2 in both runs because the baseline keeps the
repository's deprecated model. The baseline did not use web lookup in these
runs, and still chose current-looking Node and Claude IDs from memory.

A seventh case asks the agent to choose a cheaper model for ticket triage while
keeping the main model. It uses the same repository, whose main model is the
deprecated `claude-sonnet-4-5-20250929`. The mechanical assertion is pass-both
in all three baseline runs: triage uses active, cheaper Haiku 4.5. The LLM
assertion fails in all three: the baseline does not warn about the main model's
retirement.

A paired comparison was started after adding guidance to audit all pinned models
and report aged facts even when the user says to leave them alone. The old skill
scored 2/2 in all three runs; the first current-skill sample scored 2/2, 2/2,
and 1/2. After the proxy recovered, the current skill was rerun three times on
the same case: 2/2 in all three runs. The baseline's retirement-warning
assertion was 0/3, while the current skill was 3/3. This is stable evidence for
this one behavior, not a claim about every technology choice. The body change is
now committed; no full seven-case paired rerun was needed because the other six
cases are pass-both or not treated.

## `designing-modules` redesign (2026-11-01)

Anthropic and the Claude Code team have published no guidance on module boundaries,
so this skill follows primary sources instead (Parnas 1972, Fowler, Shopify, Simon
Brown, and boundary-check tool documentation; see its `references/sources.md`). It
now leads with Parnas's criterion (hide decisions likely to change), drops the
vertical-slice default no source mandates, and drops two unverified book citations.

The eval fixture is a small Python project with declared boundaries: each module has
a public `__init__` and a private `internal/` package. Checks parse every import with
`ast` (including imports inside functions) and run the tests. Each check was
validated on two to four hand-written solutions, including correct alternatives such
as duplicating a helper.

| Case | Boundaries declared (.importlinter + README) | Boundaries only in code |
|---|---:|---:|
| extract-refunds | 1.00 / 1.00 | 1.00 / 1.00 |
| fix-cycle | 1.00 / 0.83, then 1.00 / 1.00 | 1.00 / 1.00 |
| shared-formatting | 1.00 / 1.00 | 1.00 / 0.67, then 1.00 / 0.50 |

With / without skill, three runs each. The declared versions are pass-both: when the
contract is written down, the baseline follows it. The value appears when the
boundary exists only as code convention: asked to reuse billing's money formatter
from orders, the baseline imported `billing.internal.money` directly in 5 of 6 runs,
while every with-skill run exported the function through billing's public API. The
single fix-cycle difference (a baseline that broke the cycle by moving both modules'
state into a new `shop/core`) did not replicate.

One check gap was found: fix-cycle originally had no grab-bag check, so that
`shop/core` run passed. A shared-module check was added to fix-cycle and
extract-refunds, and all runs were re-graded on the same artifacts.

Cost: about +170k tokens per case, excluding one with-skill fix-cycle run that used
3.8M tokens.

Decision: retain `designing-modules`, with value limited to one well-defined
behavior: respecting code-level module boundaries that are not documented. Its
`agents-snippet.md` carries the everyday rule for projects that want it always on.

The output runs above used `deepseek-flash` and finished before its monthly cap
(all exit 0, no timeouts). The trigger run on that model was stopped when every
call began returning HTTP 429, and left no result.

Trigger evaluation on `claude-haiku-5-5` (20 queries against the implicit
extract-refunds fixture, 3 runs each): 18/20, train 11/12, validation 7/8, no
false positives, 2 infrastructure errors. The misses were:

- "this codebase is a tangle…" (train), 1/3, borderline. The description already
  says "even if the user only says the code is tangled".
- "replace the in-memory order store with a postgres-backed one, gradually"
  (validation), 0/3. Only validation failed, so the description was not changed.

A first run scored 15/20 because nine runs were excluded as errors. Several of
them were the agent asking the user a question, which aborts a non-interactive
run. Those runs are now counted (see the harness note below), and the 18/20 is
the rerun.

## `reviewing-code` trigger re-measurement (2026-11-01)

With the native-invocation fix but an empty sandbox, `reviewing-code` scored 12/20:
asked to review "my staged changes" or "PR #482" in an empty repository, the agent
ran `git status`, found nothing, and answered before choosing any skill. Trigger
queries can now name a fixture; with a small repository holding a feature branch and
a staged change, used for every positive and negative query, it scored 20/20
(train 12/12, validation 8/8). The description was unchanged across all three
measurements; only the environment changed.

## `building-llm-applications` redesign (2026-11-01)

The skill was redesigned from Anthropic's published guidance listed in
`skills/building-llm-applications/references/sources.md`: simplest architecture
first (often a single call, possibly no agent), knowledge under a few hundred pages in
the prompt instead of retrieval, task-shaped tools with detailed descriptions and
bounded, actionable responses, untrusted content kept out of the instruction channel,
and evals of 20–50 balanced cases graded on outcomes. Two earlier rules were dropped
because no source supports them: wrapping provider code behind an adapter, and
"do not expose a general-purpose tool" (the tool docs recommend consolidating related
operations).

The previous four cases were design questions whose prompts named the expected answer
("don't let the model decide authorization"), so a capable baseline passed them. They
were replaced by three fixture cases where the user asks only for a feature, and a
script runs the produced code:

| Case | Iteration 5 with / without | Iteration 6 with / without |
|---|---:|---:|
| handbook-qa (7k-token handbook; in-context vs retrieval) | 1.00 / 0.67 | 1.00 / 0.83 |
| log-search-tool (bounded, truncation notice, error instead of exception) | 1.00 / 0.67 | 1.00 / 0.67 |
| email-digest (planted instruction must not send mail) | 1.00 / 1.00 | — |
| **Mean** | **1.00 / 0.78** | **1.00 / 0.75** |

Iteration 6 re-ran only the two discriminating cases. Baseline failures were the
patterns the guidance warns about: hand-written keyword retrieval that sent only
fragments of a handbook that fits in context, a tool that truncated without telling
the model, and a tool that raised on a missing argument.

`email-digest` passed in both configurations: this model does not hand a send tool to
a summarizer unprompted. It stays in the suite as a safety regression case, not as
evidence of value.

One check defect was found and fixed during replication. The log-search check assumed
the parameter was named `query`; with-skill runs that named it `search_string` were
marked as failing while returning a correct error. The check now reads the parameter
from the tool's schema, was re-validated on six implementations, and both iterations
were re-graded on the same runs (agents were not re-run), which changed only those
with-skill verdicts.

Cost: iteration 5 shows the skill using far fewer tokens, but that is driven by one
baseline run that spent 891 s and 13.8M tokens building a retriever; in iteration 6
cost is roughly equal. The supported conclusion is that the skill does not materially
add cost, not that it saves it.

Decision: retain `building-llm-applications`.

Trigger evaluation (new query set of implicit positives and near-miss negatives,
three runs each): train 11/12, validation 7/8, one query errored. The one false
trigger is a request to write a blog post explaining retrieval-augmented generation
(2/3). It was not used to revise the description: it is a borderline single query,
and loading the skill there does not make the post wrong.

## Trigger runs that end in a question (2026-11-02)

In a non-interactive run, an agent that calls its ask-the-user tool is aborted and
exits with `error_during_execution`. The trigger harness excluded those runs as
infrastructure failures. The agent had already chosen whether to load the skill
before it asked, so excluding them dropped real routing evidence. For example,
"add logging to refund_order so we can see who issued each refund" errored in all
three runs and was recorded as having no data. The claude-code adapter now records
whether the agent asked, and such runs count. Output evals still treat them as
errors, because the run produced no work to grade.

## Trigger detection fix (2026-11-01)

The first trigger run for this skill reported 3/3 triggers on unrelated queries such as
"Rename this module" and "Update the README". Reproduction showed two causes, both
in the harness rather than the description:

1. Any tool call whose arguments mentioned `<name>/SKILL.md` counted as a load, so
   `find .claude -type f` or `ls` of the skill directory counted.
2. The trigger sandbox is empty, so the installed skill is the only file present.
   Agents asked to rename "this module" or to implement a feature opened it as the
   thing to work on, which is an ordinary file read, not routing.

Fix: only reading SKILL.md counts as a load (listing or searching does not), and for
agents with a native skill-invocation tool, trigger evals count only that tool. With
the fix the same query set scored 18/20 with no false triggers. Output evals still
count a read of SKILL.md, because their fixtures contain real code and an explicit
task; re-checking all 82 treatment-aware with-skill output runs under the new rule
changed no treatment status. Trigger results recorded before this fix, including the
`reviewing-code` false trigger on a whole-repository audit, may be inflated and
should be re-measured before acting on them.

## `reviewing-code` redesign (2026-11-01)

The skill was redesigned from the published Anthropic and Claude Code review designs
listed in `skills/reviewing-code/references/sources.md`: high-signal findings only,
refute-first verification per candidate, pre-existing defects listed separately,
explicit false-positive and security exclusion lists, and no mandatory test or
simplification pass. Its eval suite was rebuilt as paired cases: each contains a
real defect that must be reported and a decoy from the official false-positive lists
that must not be. All location assertions are mechanical checks that parse
`[path:line]` from the response; each check was validated on a good, a near-miss,
and an empty response before use.

Treatment-aware, three runs per configuration, all runs completed and treated:

| Case | Iteration 5 with / without | Iteration 6 with / without |
|---|---:|---:|
| auth-regression (cache before auth; quote-change decoy) | 1.00 / 0.83 | 1.00 / 0.83 |
| pre-existing-bug (new off-by-one; old bug must be pre-existing) | 1.00 / 0.56 | 1.00 / 0.56 |
| ssrf-host-vs-path (host-controlled must be found; path-only must not) | 0.78 / 0.67 | 0.89 / 0.67 |
| sound-change (correct change; no findings expected) | 0.50 / 0.50 | 0.56 / 0.56 |
| **Mean** | **0.82 / 0.64** | **0.86 / 0.65** |
| Cost delta | +57s / +197k tokens | +18s / +142k tokens |

Iteration 6 used a corrected `sound-change` fixture: the iteration-5 version accepted
float discounts, so with-skill runs that reported it found a real defect and the
expected answer was wrong. The no-findings check was also split so that exact verdict
wording, which only the skill prescribes, is no longer a pass condition.

The skill-only signal is consistent across both iterations on the three cases with a
real defect: it finds the authorization bypass, separates the pre-existing bug, and
reports the host-controlled SSRF more often. On the clean change both configurations
over-report at the same rate, most often by flagging a "security reviewed" comment.

Two gotchas aimed at that over-reporting were added and compared against the
previous version (`--baseline old_skill`, iteration 7): 0.97 vs 0.90, with lower cost
(-31s, -114k tokens). The difference is not attributable to the gotchas: the
previous version also scored 3/3 on `sound-change` in that iteration, and the gap
comes from single-run variance elsewhere. They were kept because they cause no
regression on the real-defect cases and restate the official "comments are not
evidence" principle, but their incremental value is unproven.

Decision: retain `reviewing-code`. This supersedes the earlier "no value" result
below, which came from a case whose decisive assertions graded style preferences.

Trigger evaluation with the adopted description: train 10/12 (one API error), validation
7/8. The remaining false positive is a whole-repository security audit request, a
validation query; it was not used to revise the description and remains a known limit.

## Treatment-aware confirmation (2026-10-31)

These are the first results from the treatment-aware harness (`ef6c8c5`): a
with-skill run counts only when its transcript proves the skill loaded; timeouts,
API errors, invalid grading, and untreated runs are excluded from the treatment
effect and reported separately. Each row is one case with three low-concurrency
runs per configuration. Results are directional evidence, not statistical proof.

| Skill / case | With skill | Baseline | Cost delta | Decision signal |
|---|---:|---:|---:|---|
| `authoring-skills` / decline generic skill | 1.00 | 0.00 | -9.6s / -96k tokens | Stable value on this case; scope still one case |
| `building-llm-applications` / private-source output | 0.89 | 0.89 | +10.0s / +99k tokens | Superseded by the 2026-11-01 redesign above |
| `designing-apis` / retryable export | 1.00 | 0.33 | +14.8s / -61k tokens | Stable value; two skill-only assertions |
| `designing-modules` / growing monolith | 1.00 | 1.00 | +5.1s / +56k tokens | Superseded by the 2026-11-01 redesign above |
| `reviewing-code` / parser-client SSRF | 0.73 | 0.80 | +68.0s / +335k tokens | Superseded by the 2026-11-01 redesign above |
| `reviewing-designs` / overbuilt project | not treated | 1.00 | — | Superseded by the 2026-11-02 redesign above |
| `selecting-technologies` / small project | 1.00 | 1.00 | +75.1s / +801k tokens | Pass-both; no measured value |
| `writing-adrs` / implicit session store | 0.89 | 0.00 | +309.6s / +2.29M tokens | Stable value, but extremely expensive |
| `writing-tests` / bug regression | 1.00 | 0.56 | +13.1s / +128k tokens | Process assertion skill-only |

A pass-both result means the case did not demonstrate incremental skill value; it
does not prove the skill is useless. Before removal, replace the case with a harder,
implicit case that the baseline demonstrably fails. If the replacement also shows no
stable gain while adding cost, removal or merging is rational. The `reviewing-code`
row was later traced to an eval defect, not a skill defect: its decisive assertions
graded whether the review discussed timeouts and one disputed parser path, while
the fixture's clearest vulnerability had no assertion at all.

The timeout/error policy and stable assertion IDs are part of the harness, not a
claim that the model is deterministic. Retry counts and all-attempt costs are
recorded; a final successful retry remains usable but its retry cost is included.

## Pre-treatment content-revision benchmark (historical, not directly comparable)

All runs below used the local cometix adapter with `deepseek-flash`, one run per
case, and a fresh sandbox per configuration. These are directional results, not
statistical conclusions.

| Skill / scope | With skill | Baseline | Interpretation |
|---|---:|---:|---|
| `authoring-skills`, decline generic skill | 1.00 | 0.00 | New guardrail prevented a generic skill artifact; one case only |
| `building-llm-applications`, 4 cases | 0.92 | 0.75 | Private-source and simple-first cases added value |
| `building-llm-applications`, revised RAG case | 1.00 | 0.67 | Split retrieval-quality and answer-quality evaluation was primary-only |
| `designing-apis`, 3 cases | 1.00 | 0.89 | Retry/authorization/old-client validation was primary-only |
| `reviewing-code`, 3 fixture cases | 1.00 | 0.93 | Concrete parser/client SSRF finding was primary-only |
| `reviewing-designs`, 3 cases | 1.00 | 1.00 | No measured quality delta; with-skill cost was higher |
| `writing-adrs`, 4 cases | 1.00 | 0.70 | Implicit shared-session-store decision was primary-only |
| `writing-tests`, original 4 cases | 0.67 | 0.67 | Bug-fix process value appeared, but total score was flat |
| `selecting-technologies`, final 3 cases | 0.89 | 0.89 | No measured quality delta; with-skill cost was higher |
| `writing-tests`, targeted feature/refactor rerun | 0.50 | 0.50 | Refactor assertion failed in both configurations; not discriminating |

The `reviewing-code` fixture suite now includes authorization/cache, migration, and
URL-parser boundary cases. Its with-skill cost was approximately `+161k` tokens and
`+17s` per case aggregate. The `reviewing-designs` run added approximately `+85k`
tokens and `+19s` with no quality delta, so no further expansion is planned there.

The first `selecting-technologies` run included a popularity-resistance case that
both configurations passed while the skill used about `+1.45M` tokens and `+170s`.
That case was removed as a non-discriminating output eval; the similar query remains
useful for trigger testing. The final three-case rerun remained at baseline parity
while adding about `+210k` tokens and `+49s`.

The `designing-modules` run is excluded: all with-skill cases finished without
loading the skill, so it measures description discovery rather than output quality.

## Current trigger evidence

### Fixture-backed re-measurement on `claude-haiku-5-5` (2026-11-02)

The queries now run in fixture repositories that hold the files they name. All
runs use 3 repetitions, and question-ending runs are counted. There were no false
positives on any skill.

| Skill | Passed | Train | Validation | Infra errors |
|---|---:|---:|---:|---:|
| selecting-technologies | 19/20 | 11/12 | 8/8 | 0 |
| designing-modules | 18/20 | 11/12 | 7/8 | 2 |
| reviewing-designs | 18/20 | 11/12 | 7/8 | 0 |
| writing-tests | 15/20 | 8/12 | 7/8 | 2 |
| writing-adrs | 12/20 | 7/12 | 5/8 | 5 (all timeouts) |

`writing-tests` and `writing-adrs` miss the implicit cases they exist for. Neither
skill was loaded for these four queries:

- "fix the 500 on /checkout"
- "add cursor pagination"
- "refactor the PDF generator"
- "we decided to drop GraphQL, record that decision"

Replaying three of the misses showed that haiku did the work itself. It wrote an
ADR that it noted lacked the reasoning, and it fixed the bug without a
regression test. That is the behaviour the skills target. Both descriptions
already list these contexts. Anthropic's guidance says agents consult skills only
for tasks beyond what they can handle alone, and that descriptions should be
imperative and "a little bit pushy". Both current descriptions open with
"Writes ...". Imperative candidates were written for both skills.

On haiku train:

- `writing-tests` went from 8/12 to 11/12. The bug-fix, pagination, and coverage
  queries rose from 0/3 to 2/3.
- `writing-adrs` went from 7/12 to 9/12, with 7 runs timing out on
  migrate-and-record queries.

The haiku validation runs were stopped when `deepseek-flash` came back, so the
adoption decision was made on `deepseek-flash`. Both versions were run on the full
query set, 3 runs each, with a 600 s timeout:

| Skill | Version | Passed | Train | Validation | False positives |
|---|---|---:|---:|---:|---:|
| writing-tests | current | 16/20 | 10/12 | 6/8 | 0 |
| writing-tests | candidate | 16/20 | 11/12 | 5/8 | 1 (vitest upgrade, 2/3) |
| writing-adrs | current | 17/20 | 10/12 | 7/8 | 0 |
| writing-adrs | candidate | 17/20 | 10/12 | 7/8 | 1 ("explain ADR vs RFC", 2/3) |

Neither candidate was adopted. The `writing-tests` candidate gained one train
query and lost one validation query, and the `writing-adrs` candidate gained
nothing; each added a false positive. This repeats the earlier `writing-tests`
result: a pushier description raises recall on its training queries and buys
false positives elsewhere.

On `deepseek-flash` the current descriptions already route better than on haiku
(16 vs 15, and 17 vs 12). Some queries stay at 0–1/3 with either wording; in each
of them the agent does the work itself:

- refactoring the PDF generator
- a flaky integration test
- a retry wrapper
- adding a second LLM provider
- websockets vs SSE

For projects that want the rule every time, the channel is each skill's
`assets/agents-snippet.md`.

### Earlier exploratory runs (deepseek-flash, empty sandbox)

The revised formal description for `writing-tests` produced `15/20` on an exploratory
run (`train` `9/12`, `validation` `6/8` among completed runs), with two provider/agent
errors excluded. Candidate descriptions reached `11/12` on train but scored worse on
validation (`5/8` with two false positives), so they were not adopted. The formal
description remains the validation-selected version.

The `evaluating-skills` baseline case for writing trigger queries timed out twice at
1200 seconds. It is excluded rather than treated as a skill failure. The current
benchmark policy does not infer quality from incomplete baseline runs.

## `evaluating-skills` redesign (2026-11-02, `deepseek-flash`)

The skill was revised to separate portable Agent Skills guidance from this
repository's harness policy. Adapter names, native invocation, treatment status,
retries, timeouts, grading, and sandbox isolation are explicitly labeled as local
policy rather than spec requirements. The workflow now states that output prompts
must not reveal the behavior under test, checks must be validated on untouched,
good, near-miss, empty, and equivalent alternatives, and any check change requires
re-grading all existing runs on the same artifacts.

The old output cases leaked their answers. They were replaced with four fixture
cases:

| Case | Purpose |
|---|---|
| review-fixture | static review of a malformed skill without naming the hidden issue |
| interpret-benchmark | classify pass-both/fail-both, primary-only, baseline-only, untreated, timeout, error, and invalid-grading records |
| design-trigger-set | create trigger queries from a domain fixture without specifying balance or implicit-case rules |
| audit-assertions | repair a contradictory assertion and validate its checks against artifact variants |

The previous `trigger_queries_valid.py` hardcoded `writing-adrs`; it now discovers
`trigger-queries.json` in the artifact or accepts a path argument.

The corrected paired run used 3 repetitions, with 11/12 treated with-skill runs
(the second design-trigger baseline timed out). Aggregate pass rate was 0.86 with
the skill versus 0.64 without, a +0.22 difference. The stable value is concentrated
in `audit-assertions`: with-skill passed 2/3 and baseline 0/3 on both mechanical
assertions. `design-trigger-set` and `review-fixture` passed in both configurations.
`interpret-benchmark` improved on one mechanical separation/cost assertion but
remained noisy.

Cost was about +131 seconds per run. Token totals are not comparable in the simple
aggregate because the baseline included a very long trigger-query run and one
baseline timeout; report the raw per-case values rather than treating the negative
aggregate token delta as a general cost saving. The assertion-audit check was fixed
after the first grading pass to inspect the repaired `eval.json`, generated scripts,
and good/near-miss/empty artifacts; all paired runs were re-graded on the same
artifacts. The trigger-query and benchmark checks were also validated on good and
near-miss responses.

Decision: retain, with a narrow measured benefit: it helps an evaluator detect and
repair an assertion that contradicts the fixture schema and test the repair across
artifact variants. The other methodology claims are not independently demonstrated
by these cases.

## `writing-tests`

Iteration 2 benchmark:

| Eval | With skill | Without skill |
|---|---:|---:|
| Bug fix / regression test | 1.00 | 0.67 |
| Feature without an explicit test request | 1.00 | 1.00 |
| Flaky test repair | 1.00 | 0.83 |
| Refactor of untested code | 1.00 | 0.00 |
| **Mean** | **1.00** | **0.62** |

Cost:

- Mean time: 51.90s vs 29.62s (`+22.28s`)
- Mean tokens: 69,566 vs 27,314 (`+42,252`)

Observed value:

- The skill caused the agent to run a new regression test before changing production
  code in the successful run.
- It preserved production expiry semantics while replacing real sleeps with a
  controllable clock.
- It added characterization tests before refactoring previously untested code.
- Mechanical checks tested the agent's tests against the original fixture and against
  plausible wrong implementations.

Caveat: the feature case was easy enough that the baseline also passed. It measures
that the agent can handle the feature, not much incremental skill value. More future
cases should target implicit test obligations and difficult edge cases.

## `writing-adrs`

Iteration 2 benchmark:

| Eval | With skill | Without skill |
|---|---:|---:|
| Add durable queue decision record | 0.88 | 1.00 |
| Supersede polling decision with SSE | 0.90 | 0.90 |
| Do not create ADR for trivial CLI change | 1.00 | 1.00 |
| Implicitly record shared session-store decision | 1.00 | 0.50 |
| **Mean** | **0.94** | **0.85** |

Cost:

- Mean time: 49.88s vs 43.46s (`+6.42s`)
- Mean tokens: 98,505 vs 78,052 (`+20,453`)

Observed value:

- The skill recognized an implicit architectural decision and created an ADR without
  being explicitly asked for one.
- It preserved the project's existing ADR numbering and heading style after the skill
  was tightened to prefer local conventions over its bundled template.
- It distinguished a costly decision from a reversible trivial CLI change.

Caveat: one ADR case still has baseline parity. The benchmark is evidence that the
skill helps with implicit decision capture, not proof that every ADR will be correct.

## Trigger evals

An initial Pi trigger run was made before the final low-concurrency/rate-limit handling
was stabilized:

- `writing-tests`: 11/20 queries passed.
- `writing-adrs`: 15/20 queries passed.

The results showed false positives and false negatives that require description tuning.
They should not be treated as final because the run was concurrent and the provider hit
rate limits in a later output-eval round. Re-run with `--jobs 1`, three repetitions,
and inspect train versus validation separately before changing descriptions.

## Interpretation rules

- A skill is valuable when it improves behavior the user did not explicitly request,
  not merely when it answers an explicit instruction better.
- Assertions that pass in both configurations are non-discriminating; replace them or
  drop them from the value calculation.
- An agent API error or rate limit is not a skill failure. Re-run it and exclude it from
  the benchmark if it remains errored.
- A skill's extra tokens/time are part of its cost. Compare them against the quality
  delta and the severity of failures prevented.
- Results do not transfer between Pi, Nyan, Claude Code, Codex, or different models.
