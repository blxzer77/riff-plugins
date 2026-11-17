## Invariant checks

- Models and invariant checks in this repository are findings machines: when one
  fails, fix the code or show the model wrong. Never weaken the invariant, drop an
  action or add a constraint to get green.
- After changing code a model covers, update the model from the code, rerun it, and
  confirm the check still fails on a deliberately broken variant.
- Replay every counterexample on the real code as a test before calling it a bug.
