# plugins

One directory per plugin. Today: [`riff-web`](riff-web), which wires the
`riff web` command into each agent's web tools.

## How each agent finds a plugin

The four agents disagree about where a plugin lives, and two of them cannot
install from a subdirectory at all. The layout follows what each one requires
(verified 2026-11-19 against the vendors' docs):

| Agent | Where it looks | Why there |
|---|---|---|
| Claude Code | `plugins/riff-web/.claude-plugin/plugin.json` + `hooks/hooks.json`, listed in `.claude-plugin/marketplace.json` | A marketplace entry may point at a subdirectory |
| Codex | Nothing: see [riff-web/codex.md](riff-web/codex.md) | Hosted tools bypass hooks, and Codex already exports `CODEX_SESSION_ID`; a config line is enough |
| Antigravity | `.antigravity-plugin/plugin.json` + `hooks.json` at the **repository root** | `agy plugin install <repo>` takes no subdirectory |
| pi | `package.json` with a `pi` field at the **repository root** | `pi install git:…` installs the repository root only |

Antigravity and pi therefore share the root with the skill-only `riff` plugin.
The root `hooks.json` is Antigravity's; `.antigravity-plugin/plugin.json` takes
precedence over a root `plugin.json`, which is what lets the same root also be
a pi package and a Claude Code marketplace.

## Conventions

- `plugins/<plugin>/source.json` is the only hand-written manifest. It holds the
  name, version, description, and each agent's hook commands.
- Every other manifest is generated from it by
  `python3 scripts/gen-manifests.py`; CI runs that with `--check` and fails on a
  stale file. Do not edit a generated manifest by hand.
- Skills are not copied into a plugin. A plugin lists them, or relies on the
  root `riff` plugin, so `skills/` stays the only source.
- A plugin that needs a feature names its command (see
  [features/README.md](../features/README.md)); the user installs the feature
  separately, and the adapter degrades to the built-in tool when the command is
  missing or unconfigured.
