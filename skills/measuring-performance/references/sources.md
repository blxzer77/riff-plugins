# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; its checklist is rewritten here
and checked against the sources below. Read on 2026-11-16.

| Source | What this skill takes from it |
|---|---|
| Brendan Gregg, "Active Benchmarking" and *Systems Performance* (2nd ed., 2020) | Find what limits a benchmark while it runs; a number without its limiter is not understood |
| Gene Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities" (1967) | Speedup is bounded by the share of time the improved part takes |
| Python 3.15 documentation, `timeit` and "profiling — Python profilers" | The profilers give an execution profile, "not for benchmarking purposes"; time with `timeit`. 3.15 adds `profiling.sampling` and `profiling.tracing` and deprecates `profile` |
| pstack `skills/benchmark-checklist/SKILL.md`, `skills/principle-explain-the-number/SKILL.md` (`cursor/plugins` `bf0c7cd`, MIT) | Write the claim first; "why not double?"; check limits, errors, repeatability (alternate sides, median and range) and that the work happened; verdicts include "no measurable difference" and "inconclusive" |

URLs:

- https://www.brendangregg.com/activebenchmarking.html
- https://www.brendangregg.com/systems-performance-2nd-edition-book.html
- https://docs.python.org/3/library/timeit.html
- https://docs.python.org/3/library/profiling.html
- https://github.com/cursor/plugins/tree/main/pstack
