## Fan-out work

- List every slice before starting; the final report accounts for each one.
- Each worker that writes or applies anything gets its own copy of the tree.
- Workers return PASS, ISSUES (all provable problems) or BLOCKED (could not check,
  why), with evidence. Gaps and BLOCKED are not passes.
- For a race between alternatives, state the selection rule before measuring and
  measure every attempt the same way.
- Report one table, not raw worker output; check, do not fix, unless asked.
