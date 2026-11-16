# Verifying a candidate

Verified on 2026-11-16. Adapted from the verifier designs listed in `sources.md`.

Each candidate gets one job: try to disprove it. It is reported only if that fails.

## The standard

Keep a candidate only when you can cite, at `file:line`:

1. **Cause** — the changed line that introduces or reaches the defect.
2. **Trigger** — a supported input, caller, or state that reaches it. For security
   findings, name who authors that input and the line that shows the code trusts
   them.
3. **Consequence** — what breaks or what the attacker gains beyond what their
   position already allows.
4. **No defense** — the guard, type, framework default, or caller check you looked
   for and did not find.

"Looks risky", "violates best practice", or "could break in some configuration" is
not enough. Neither is a candidate you could not fully trace; say what stopped you
and drop it.

Do not invent a defense to kill a finding either. Refute only with a mitigation you
located and read. "The framework probably escapes this" is a reason to go read the
framework call, not a refutation.

## Run it when you can

A candidate you can show by running something is stronger than one you traced. If
a failing test, a short script against the changed code, or a command would show
the defect, run it and keep the output with the finding. Work in a scratch
location and leave the tree under review unchanged. If the run does not show the
failure, drop the candidate; do not keep it on the strength of the argument.

## Consumers a search does not show

A symbol search finds callers, not everything that depends on the changed value.
Before clearing a change to a name, a shape, or a default, look where the search
stops: serialized data another program reads, keys built from strings,
configuration and templates, feature flags, and code in another language that
reads the same bytes. A search that finds nothing is still a result; say what you
searched for.

## Pre-existing or introduced

Compare the candidate's source, sink, guards, and routes with the pre-change code.
If all of them read the same before the change, the defect is pre-existing: report
it in the separate section, not as a finding of this review. A new caller, route, or
input that the change adds to an old sink is the change taking part, so it is a
finding.

## Confidence and severity

Rate confidence 0–100 that all four parts hold. Report at 80 or above; below that,
drop it. Severity follows the consequence the code supports, not the one the claim
asserts: `important` for a defect that should block merge, `nit` for a real but
minor one. Lower a severity when verification shows a hurdle; never raise it to
make a finding more persuasive.

## Independence

The candidate's author is the worst verifier: they already believe it. When the
environment supports independent workers, give each candidate to a fresh one with
the claim, the diff, and repository access, but not the reasoning that produced the
claim. When it does not, re-read the cited lines from scratch before keeping it.

When several passes or reviewers produce candidates, verify each and keep every
one that survives, merging those with one root cause. Do not vote: reviewers find
different defects, so a finding only one of them raised is no weaker for it.
