# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; its practices are rewritten here
and checked against the sources below. Read on 2026-11-16.

| Source | What this skill takes from it |
|---|---|
| Claude Code docs, "Best practices for Claude Code" (fetched 2026-11-16) | Give the agent a way to verify its work; ask for evidence, the command it ran and its output, because "all tests pass" on its own tells you very little |
| pstack `skills/principle-prove-it-works/SKILL.md` (`cursor/plugins` `bf0c7cd`, MIT) | Verify against the real artifact, not a proxy, a self-report or "it compiles"; script the check when you can |
| pstack `skills/blast-radius/SKILL.md` and `skills/poteto-mode/playbooks/bug-fix.md` (same commit) | Look for consumers a symbol search does not show; "inconclusive" or the wrong surface is not a pass |

URLs:

- https://code.claude.com/docs/en/best-practices
- https://github.com/cursor/plugins/tree/main/pstack
