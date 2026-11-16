## Performance

- Measure the real path before optimizing, and find the hot spot with a profiler,
  not by reading code.
- Keep output identical; compare old and new on the same input.
- Repeat measurements (median and range); a gap smaller than the run-to-run spread
  is no difference.
- A single benchmark run or CI alert is a reason to measure, not proof of a
  regression.
- Report before/after numbers, run count, and what bounds the result.
