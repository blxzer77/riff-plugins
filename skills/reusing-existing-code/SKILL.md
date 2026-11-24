---
name: reusing-existing-code
description: "Keeps one implementation of each rule while changing existing code. Use when adding a function, endpoint, export, validation or variant to a codebase that may already do something similar, or before copying code to make a new case. Not for splitting modules or reviewing diffs."
license: Apache-2.0
metadata:
  verified-on: "2026-11-24"
---

# Reusing existing code

Each rule (a validation, a normalization, a file format, a price) belongs in one
place that the rest of the code calls. A second copy drifts from the first until two
paths accept different data, and every later change has to find both.

## Workflow

- [ ] **Search for the rule by what it does, not only by name.** Before writing it,
      look for the same regular expression, constant, error message or field names
      elsewhere; the function you need may be named for another caller's concept.
      If it exists, call it through its module's public interface, adding a
      parameter or a public function there if the new caller needs one.
- [ ] **Tidy first, then add.** If the change would copy logic that already exists
      (a rule another path implements, or a block repeated once per variant), first
      move that logic into one function in the module that owns it and switch the
      existing callers to it, with the tests passing and behavior unchanged. Then
      build the new case on that function.
- [ ] **Do not merge look-alikes.** Code that only looks the same, because it
      encodes decisions that change for different reasons, stays separate. If
      sharing it needs a flag or a branch per caller, it is the wrong abstraction.

## Gotchas

- "Follow the existing pattern" means the shape of the code, not another copy of the
  block. Three copies of one block are a function waiting to be extracted.
- The shared function belongs to the module that owns the rule, not to a new `utils`
  or `common` module that everything imports and no one owns.

## References

- `references/sources.md` — the published sources this skill follows.
