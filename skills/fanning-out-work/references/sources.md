# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; its swarm protocol is rewritten
here in tool-neutral terms. Read on 2026-11-17.

| Source | What this skill takes from it |
|---|---|
| Anthropic, "Building effective agents" (2024), section "Parallelization" (fetched 2026-11-17) | Two forms: sectioning (independent subtasks in parallel) and voting (the same task several times); aggregate programmatically |
| pstack `skills/swarm/SKILL.md` (`cursor/plugins` `3fa33bb`, MIT) | Frame the done predicate and the shape (slices, race, mixed); declare the race rule before spawning; own writable output per worker; standalone briefs naming exact SHAs and method; PASS / ISSUES / BLOCKED with every provable issue; proceed with N-1 on dropout; one retry for a result missing required fields, then a gap; gaps are not passes; one consolidated report |
| pstack `skills/arena/SKILL.md`, `skills/interrogate/SKILL.md` (same commit) | Races repeat one brief and pick a base; coverage is a partition, not a race |

URLs:

- https://www.anthropic.com/engineering/building-effective-agents
- https://github.com/cursor/plugins/tree/main/pstack
