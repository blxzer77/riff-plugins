# plugins

One directory per plugin. None yet; the skills are currently published as the
`riff` plugin straight from the repository root (`.claude-plugin/marketplace.json`).

## Conventions

- `plugins/<plugin>/` holds each agent's manifest side by side, for example
  `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and
  `.antigravity-plugin/plugin.json`.
- Skills are not copied into a plugin. A plugin refers to directories under
  `skills/`, so `skills/` stays the only source.
- Manifests are generated from one description of the plugin, and CI fails when a
  generated manifest differs from the committed one. Do not edit them by hand.
- A plugin that needs a feature names its command (see `features/README.md`); the
  user installs the feature separately.
