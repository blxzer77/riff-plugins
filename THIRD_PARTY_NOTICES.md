# Third-party notices

## SDFrame (Caldis/frameworks)

Source: https://github.com/Caldis/frameworks, commit
`e519d0dd4d16be63b956fd35ab52fd6644840328`.

Used as source material only: topic selection and reading lists for skill references.
Skill content in this repository is rewritten and checked against the primary
sources it cites; no upstream text is reproduced verbatim. The mapping from upstream
entries to skills, and the reason each excluded entry was cut, is in
`sources/sdframe.yaml`.

The upstream README states the MIT License; at the pinned commit the repository
contains no LICENSE file.

## Agent Skills evaluation method

The evaluation workflow, file formats, and grader/comparator/analyzer roles in
`skills/evaluating-skills/` are adapted from the Agent Skills documentation
(https://agentskills.io) and Anthropic's `skill-creator` skill
(https://github.com/anthropics/skills, Apache-2.0). Changes: vendor-neutral agent
adapters, per-run sandboxes, unified field names, baseline-relative deltas, and
rewritten role prompts.

## pstack

Source: https://github.com/cursor/plugins/tree/main/pstack, commit
`bf0c7cd80abdbf7fe47b634978a7d1b4071f71a7`. MIT License, Copyright (c) 2026 Lauren
Tan.

Used as source material for practices in `writing-tests`, `designing-modules`,
`reviewing-code`, `reviewing-designs`, and `authoring-skills`; for the new skills
`debugging-failures`, `writing-typescript`, `verifying-changes`, and
`measuring-performance`; and for the rule table in `AGENTS.md`. The
practices are rewritten in this repository's words and checked against a primary
source where one exists; no upstream text is reproduced. The mapping from upstream
files to skills, and what was left out and why, is in `sources/pstack.yaml`.

## Review, design-review, technology-selection, and LLM-application guidance

Principles in `reviewing-code`, `reviewing-designs`, `selecting-technologies`, and
`building-llm-applications` are adapted from the sources below and rewritten in this
repository's words; no upstream text is reproduced. The files used from each source
are listed in `sources/anthropic-review.yaml`, `sources/anthropic-design-review.yaml`,
`sources/anthropic-tech-selection.yaml`, and `sources/anthropic-llm-apps.yaml`.

- `anthropics/claude-plugins-official`, commit
  `a7ba5b93db0c7c8d17f3f1d25853adca79598a1a`, Apache-2.0: code-review, security,
  pull-request review, feature-development, architecture-critic, and version-checking
  guidance.
- `anthropics/claude-code-security-review`, commit
  `0c6a49f1fa56a1d472575da86a94dbc1edb78eda`, MIT: security-review command, findings
  filter, and prompts.
- `anthropics/claude-cookbooks`, commit `c43f56d0360b9b1f631bd090fd199231d4c880cc`,
  MIT: agent workflow patterns and retrieval evaluation.
- "Concise Guide for Evaluating Open Source Software" by the OpenSSF Best Practices
  Working Group (`ossf/wg-best-practices-os-developers`, commit
  `b8ea05ab5c3b2ae341301dfe4f7783dc111f2841`), licensed CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/). Changes: evaluation criteria
  condensed and rewritten as checks an agent runs.
- `ossf/scorecard`, commit `2ef237f4e967d18e600e71aa36ab3be640314650`, Apache-2.0:
  check definitions used as reference criteria.
- `nodejs/Release`, commit `c3e8696312969c95643cb52f05f124c161db87b2`: the release
  schedule is cited as a data source to query at run time; nothing is copied, and the
  repository has no license file at that commit.
- Anthropic engineering posts and Claude documentation pages, cited by URL and fetch
  date in each skill's `references/sources.md`.
