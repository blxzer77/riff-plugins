# Sources

pstack (`cursor/plugins`, MIT) prompted the skill; the practices are rewritten here
and checked against the published sources below. Read on 2026-11-16.

| Source | What this skill takes from it |
|---|---|
| David J. Agans, *Debugging: The 9 Indispensable Rules for Finding Even the Most Elusive Software and Hardware Problems* (AMACOM, 2002) | Make it fail before fixing; quit thinking and look at the actual state; change one thing at a time; if you didn't fix it, it ain't fixed |
| Andreas Zeller, *Why Programs Fail: A Guide to Systematic Debugging* (2nd ed., Morgan Kaufmann, 2009) | Debugging as the scientific method: hypotheses tested by experiment; trace the infection chain from failure back to the defect |
| Git documentation, `git bisect` | Binary search between a known good and a known bad version |
| pstack `skills/principle-fix-root-causes/SKILL.md` and `skills/poteto-mode/playbooks/bug-fix.md` (`cursor/plugins` `bf0c7cd`, MIT) | Ask whether the triggering state is legitimate; guards, retries, swallowed errors and clamped values hide bugs; revert what a refuted hypothesis motivated; fix every instance of the pattern; show the reproduction failing, then passing |

URLs:

- https://debuggingrules.com/
- https://www.whyprogramsfail.com/
- https://git-scm.com/docs/git-bisect
- https://github.com/cursor/plugins/tree/main/pstack
