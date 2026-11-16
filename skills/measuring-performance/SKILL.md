---
name: measuring-performance
description: Measures before and after any speed or resource claim. Use when asked to make code faster or leaner, find a slowdown, check a benchmark or perf alert, or decide whether one implementation is faster than another. Not for load-test or monitoring setup, or tuning infrastructure you cannot measure here.
license: Apache-2.0
metadata:
  verified-on: "2026-11-16"
---

# Measuring performance

Performance work goes wrong in two ways: optimizing what was never slow, and
believing a number that measured something else. Both come from guessing. Measure
the real workload, find what limits it, change that, and report numbers that would
survive someone running them again.

## Workflow

- [ ] **Write down the claim you expect to make.** "The export takes under a second
      for 20k orders" or "dedupe_fast is faster on our inputs and returns the same
      result". It tells you what to measure and when to stop.
- [ ] **Measure the baseline first, on the real path.** Use the project's script or
      the command the user runs, with realistic data sizes. Record the number before
      changing anything.
- [ ] **Find the limiter with a profiler, not by reading code.** Use a sampling or
      deterministic profiler (Python's `cProfile`, or `profiling.sampling` and
      `profiling.tracing` from 3.15; `py-spy`, `node --cpu-prof`, `perf`) in a
      run you do not report, and map the hot spot to source. The user's suspect is a
      hypothesis; say so when the profile points elsewhere.
- [ ] **Change the limiter, and keep behavior identical.** Compare the output of the
      new code with the old on the same input (byte for byte when it is data). A
      faster function that returns something different is a different function.
- [ ] **Measure again the same way, more than once.** Repeat each side several times
      (at least five for close calls), alternating old and new, and report the median
      and the range. A difference smaller than the run-to-run spread is no measured
      difference.
- [ ] **Report** in the format below, leading with the verdict.

## Judging a number

- **Name what bounds it.** If you cannot say why the result is not twice as good
  (a core, a lock, I/O, an algorithm, the benchmark harness), you do not yet know
  what you measured.
- **Check the arithmetic.** Removing a part that takes 10% of the run makes the run
  at most about 11% faster (Amdahl's law). A speedup larger than the time the
  changed part took means the measurement is wrong.
- **Check that the work happened and succeeded.** Errors and rejections are fast;
  lazy code that nobody consumes takes no time. Count failures and check outputs.
- **Use more than one input size** when choosing between implementations. Constant
  factors win on small inputs and complexity wins on large ones.
- **A single run is an anecdote.** A CI alert from one run on a shared machine is a
  reason to measure, not evidence of a regression. If the change cannot plausibly
  cost time (a rename, a comment), say so, rerun both versions on one machine, and
  report "no measurable difference" when that is what the runs show. Do not
  "optimize" something to answer an alert you could not reproduce.

## Report

```text
Verdict: <faster | slower | no measurable difference | inconclusive>
Numbers: <before -> after, unit, runs per side, median and range, input size>
Limiter: <what bounds it, and the profile or counter that shows it>
Behavior: <how you checked the output is unchanged>
Not measured: <what you could not run (production data, concurrency, other machines)>
```

Call the result inconclusive when you could not name the limiter, could not check
correctness, or the spread is as large as the effect.

## Gotchas

- Profilers slow the code down and distort small functions; profile to find the
  hot spot, then time without the profiler.
- The first run pays for imports, JIT warmup, and cold caches. Warm up, or report
  cold and warm separately when users see both.
- `timeit` and similar harnesses run tiny inputs many times. Check that the result
  holds for the sizes the code actually sees.
- Faster code that changes ordering, rounding, or error behavior breaks callers who
  never asked for speed. Read the callers before switching them.

## References

- `references/sources.md` — the measurement guidance this skill follows.
- `assets/agents-snippet.md` — copy into the project's agent instruction file for always-on performance defaults.
