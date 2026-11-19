# features

Features that plugins ship to coding agents, such as command-line tools. None yet.

## Conventions

- One feature per directory: `features/<name>/`.
- A feature is a program on the user's `PATH`, released as prebuilt binaries for
  each platform on GitHub Releases. No agent installs binaries per platform, so a
  plugin only names the command; it never bundles or downloads the program.
- The language is chosen per feature, for compatibility and performance.
- An agent learns to use a feature from a skill under `skills/`, not from text
  inside the feature directory. A feature may also offer an MCP server mode when
  an agent needs one.
- Each feature is versioned and tagged on its own as `<name>-vX.Y.Z`. Plain
  `vX.Y.Z` tags stay reserved for the skills, which installers fetch by repository tag.
