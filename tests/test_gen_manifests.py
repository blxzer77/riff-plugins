"""The generated manifests match the source, and each has the shape its agent
requires (checked against the vendors' docs on 2026-11-19)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

# The script's name has a hyphen, so it cannot be imported by name.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_manifests", REPO / "scripts" / "gen-manifests.py")
gen_manifests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_manifests)


class GeneratedManifests(unittest.TestCase):
    def setUp(self):
        self.source = gen_manifests.load()

    def test_committed_files_are_current(self):
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "gen-manifests.py"), "--check"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")

    def test_claude_code_hooks_are_wrapped_and_match_the_builtin_tools(self):
        hooks = json.loads(gen_manifests.claude_hooks(self.source))["hooks"]
        # A bare event map fails to load in Claude Code; it needs the wrapper.
        pre = hooks["PreToolUse"][0]
        self.assertEqual(pre["matcher"], "WebSearch|WebFetch")
        self.assertEqual(pre["hooks"][0]["type"], "command")
        self.assertIn("--agent claude-code", pre["hooks"][0]["command"])
        # No matcher on SessionStart: it fires for every session start.
        self.assertNotIn("matcher", hooks["SessionStart"][0])
        self.assertIn("sessionstart", hooks["SessionStart"][0]["hooks"][0]["command"])

    def test_antigravity_hooks_are_named_groups_with_a_regex_matcher(self):
        hooks = json.loads(gen_manifests.antigravity_hooks(self.source))
        self.assertEqual(list(hooks), ["riff-web"])
        pre = hooks["riff-web"]["PreToolUse"][0]
        self.assertEqual(pre["matcher"], "search_web|read_url_content")
        self.assertIn("--agent antigravity", pre["hooks"][0]["command"])

    def test_the_pi_package_points_at_existing_files(self):
        package = json.loads(gen_manifests.package_json(self.source))
        for extension in package["pi"]["extensions"]:
            self.assertTrue((REPO / extension).is_file(), extension)
        for skill_root in package["pi"]["skills"]:
            self.assertTrue((REPO / skill_root).is_dir(), skill_root)

    def test_the_claude_plugin_lists_the_skill_separately(self):
        # The plugin is hook-only; the skill ships in the root `riff` plugin.
        plugin = REPO / "plugins" / "riff-web"
        self.assertFalse((plugin / "skills").exists())
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        names = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn("./skills/searching-the-web", names["riff"]["skills"])
        self.assertEqual(names["riff-web"]["source"], "./plugins/riff-web")

    def test_capabilities_are_declared_for_every_agent(self):
        for agent in ("claude_code", "antigravity", "pi"):
            self.assertIn(agent, self.source)
        # Codex has no manifest on purpose; its wiring is documented instead.
        self.assertTrue((REPO / "plugins" / "riff-web" / "codex.md").is_file())


if __name__ == "__main__":
    unittest.main()
