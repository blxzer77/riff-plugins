# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; its generator and maintenance
loop are rewritten here for any agent that loads project skills. Read on 2026-11-17.

| Source | What this skill takes from it |
|---|---|
| pstack `skills/create-verification-skill/SKILL.md` and `references/feature-map-example/` (`cursor/plugins` `3fa33bb`, MIT) | Interview the repository; Launch, Doctor, Drive, Evidence, Cleanup and Helpers sections; ready means usable; kill only what you started; evidence survives cleanup; a feature map with user entry points; never weaken a journey; prove the generated skill once; list what a stand-in did that the target will not |
| pstack `skills/maintain-verification-skill/SKILL.md` (same commit) | Drive every mapped feature live; classify failures as doc drift, harness gap or product gap; edit only the skill's folder; never paper over a product regression |
| Claude Code docs, "Best practices for Claude Code" (fetched 2026-11-16) | Give the agent a way to verify its work, and ask for evidence |
| Agent Skills specification | Project-local skills are folders with a `SKILL.md` whose frontmatter names the skill and says when to use it |

URLs:

- https://github.com/cursor/plugins/tree/main/pstack
- https://code.claude.com/docs/en/best-practices
- https://agentskills.io/specification
