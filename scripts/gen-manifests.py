#!/usr/bin/env python3
"""Render every agent's plugin manifest from `plugins/riff-web/source.json`.

Hand-written manifests drift: a version bump here, a renamed command there, and
one agent keeps calling a command that no longer exists. The source file is the
only place those values live; this script writes the others and CI runs it with
`--check` to fail when a committed file differs.

  python3 scripts/gen-manifests.py           # write the derived files
  python3 scripts/gen-manifests.py --check   # exit 1 if any file is stale

Where each agent looks (verified 2026-11-19 against the vendors' docs):

- Claude Code: `plugins/riff-web/.claude-plugin/plugin.json` (skill-less; the
  skill comes from the root `riff` plugin) and `hooks/hooks.json`.
- Antigravity: the repository root is the plugin root, because `agy plugin
  install <repo>` takes no subdirectory. `hooks.json` sits at the root.
- pi: the repository root is the package root; `package.json` carries the `pi`
  field. TypeScript extensions load without compilation.
- Codex: no manifest. Hosted tools cannot be intercepted by a hook, and Codex
  already exports `CODEX_SESSION_ID` to every shell command, so there is
  nothing for a hook to do; `docs/design.md` says to disable `web_search`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "plugins" / "riff-web" / "source.json"


def load() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def plugin_manifest(source: dict) -> str:
    """`.claude-plugin/plugin.json`: name, version, description, hooks path."""
    manifest = {
        "name": source["name"],
        "version": source["version"],
        "description": source["description"],
        **source["claude_code"]["manifest"],
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def claude_hooks(source: dict) -> str:
    """Claude Code `hooks/hooks.json`.

    The event map goes inside a top-level `hooks` key; a file with only the
    events fails to load. `matcher` is a pipe-separated list, matched exactly
    for these names.
    """
    events = {}
    for event, spec in source["claude_code"]["hooks"].items():
        entry = {
            "hooks": [
                {
                    "type": "command",
                    "command": spec["command"],
                    "timeout": spec["timeout"],
                }
            ]
        }
        if spec["matcher"]:
            entry = {"matcher": spec["matcher"], **entry}
        events[event] = [entry]
    return json.dumps({"hooks": events}, indent=2, ensure_ascii=False) + "\n"


def antigravity_manifest(source: dict) -> str:
    manifest = {
        "$schema": "https://antigravity.google/schemas/v1/plugin.json",
        "name": source["name"],
        "version": source["version"],
        "description": source["description"],
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def antigravity_hooks(source: dict) -> str:
    """Antigravity `hooks.json`: named groups of event lists; `matcher` is a regex.

    Hooks run with cwd at the plugin root and must exit 0; ours exits 0 even
    when it lets a call through, so a riff problem never blocks the tool.
    """
    events = {}
    for event, spec in source["antigravity"]["hooks"].items():
        events[event] = [
            {
                "matcher": spec["matcher"],
                "hooks": [
                    {
                        "type": "command",
                        "command": spec["command"],
                        "timeout": spec["timeout"],
                    }
                ],
            }
        ]
    return json.dumps({source["name"]: events}, indent=2, ensure_ascii=False) + "\n"


def package_json(source: dict) -> str:
    """The repository root as a pi package.

    pi installs from a git repository root only, so the package root and the
    plugin root are the same place. `skills/` is a glob because the skills are
    one directory per skill.
    """
    package = {
        "name": source["name"],
        "version": source["version"],
        "description": source["description"],
        "private": True,
        "pi": {
            "extensions": [source["pi"]["extension"]],
            "skills": ["./skills"],
        },
    }
    return json.dumps(package, indent=2, ensure_ascii=False) + "\n"


def targets(source: dict) -> dict[Path, str]:
    return {
        REPO / "plugins" / "riff-web" / ".claude-plugin" / "plugin.json": plugin_manifest(source),
        REPO / "plugins" / "riff-web" / "hooks" / "hooks.json": claude_hooks(source),
        REPO / ".antigravity-plugin" / "plugin.json": antigravity_manifest(source),
        REPO / "hooks.json": antigravity_hooks(source),
        REPO / "package.json": package_json(source),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a generated file is stale")
    args = parser.parse_args()
    source = load()
    stale = []
    for path, content in targets(source).items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == content:
            continue
        if args.check:
            stale.append(path.relative_to(REPO))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    if stale:
        print("stale generated manifests (run scripts/gen-manifests.py):", file=sys.stderr)
        for path in stale:
            print(f"  {path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
