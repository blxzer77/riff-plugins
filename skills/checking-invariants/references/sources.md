# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; its practices are rewritten here
and checked against the sources below. Read on 2026-11-17.

| Source | What this skill takes from it |
|---|---|
| Leslie Lamport, *Specifying Systems* (2002) and the TLA+ home page | Specifications as initial state plus next-state actions; invariants checked over every reachable state |
| `tlaplus/tlaplus` GitHub releases, `tla2tools.jar` v1.7.4 (run locally 2026-11-17 on Java 25) | TLC command line, config syntax, `-deadlock`, `-workers 1`, stopping at the first violated invariant, trace format |
| Hypothesis documentation, "Stateful tests" (`RuleBasedStateMachine`) | Stateful property-based testing as the code-level way to explore sequences of calls |
| pstack `skills/create-formal-verification-skill/SKILL.md`, `skills/maintain-formal-verification-skill/SKILL.md`, `skills/statechart/SKILL.md` (`cursor/plugins` `3fa33bb`, MIT) | Choose the strongest target, let the question choose the tool, true to the code, able to fail, findings stay findings, record the sync commit, update from the code not the result, replay each bug path on the real code, remove a broken rule and rerun |

URLs:

- https://lamport.azurewebsites.net/tla/tla.html
- https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4
- https://hypothesis.readthedocs.io/en/latest/stateful.html
- https://github.com/cursor/plugins/tree/main/pstack
