# Codex

Codex needs no plugin. Two things differ from the other agents:

- **The hosted web search cannot be intercepted.** A PreToolUse hook never sees
  it (Codex hooks docs: hosted tools such as `WebSearch` — "No" for both
  matching and blocking), so riff turns it off in configuration instead.
- **The session id is already in the environment.** Codex exports
  `CODEX_SESSION_ID` to every shell command, and riff reads it when neither
  `--session` nor `RIFF_SESSION` is set. Nothing needs to pass it along.

## Turn off the built-in search

In `~/.codex/config.toml` (or a trusted project's `.codex/config.toml`):

```toml
# riff does the searching; the hosted tool would bypass it.
web_search = "disabled"
```

`web_search` takes `disabled`, `cached`, `indexed` or `live` and defaults to
`cached`. Leave browser features as they are: they open pages for a person,
not the model.

## Install the skill

The `searching-the-web` skill comes from the repository root:

```bash
npx skills add blxzer77/riff-plugins --skill searching-the-web
```

or point Codex at the repository with `codex plugin marketplace add
blxzer77/riff-plugins` and install the root `riff` plugin, which lists the
skills.

Without either, the model has no instructions to use `riff` and the built-in
tool is off, so the agent loses the web. Install one of them first.

## Output size

Codex keeps a command's output up to the model's truncation budget and cuts the
middle out of anything longer. For every model in Codex's catalog that budget
is 10,000 tokens, counted as 40,000 bytes, so riff's 30,000-byte output arrives
whole (codex-rs rust-v0.170.0, checked 2026-11-19). Two cases lower it: a model
name Codex does not know falls back to 10,000 bytes, and `tool_output_token_limit`
in `config.toml` sets it directly. In either case ask riff for less:

```bash
riff web fetch <url> --max-bytes 8000   # the continuation command keeps the cap
```

## Check

```bash
riff web doctor        # providers, keys, proxy, cooldowns
echo $CODEX_SESSION_ID # non-empty inside a Codex shell command
```
