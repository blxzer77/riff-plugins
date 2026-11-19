# features

Features that plugins ship to coding agents, such as command-line tools. Today:
[`web`](web), the `riff web` search and page fetch.

## Conventions

- One feature per directory: `features/<name>/`.
- Every feature is a subcommand of one program, `riff`, which sits on the user's
  `PATH` and is released as prebuilt binaries for each platform on GitHub
  Releases. No agent installs binaries per platform, so a plugin only names the
  command; it never bundles or downloads the program.
- An agent learns to use a feature from a skill under `skills/`, not from text
  inside the feature directory. A feature may also offer an MCP server mode when
  an agent needs one.
- The `riff` binary and the plugins share one release line, tagged
  `riff-vX.Y.Z`. Plain `vX.Y.Z` tags stay reserved for the skills, which
  installers fetch by repository tag.
- The design is in [docs/design.md](../docs/design.md).
