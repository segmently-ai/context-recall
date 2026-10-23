import json
import shutil
import tempfile
import unittest
from pathlib import Path

from export import export
from tests.helpers import STAND, run


class StandInMcp(unittest.TestCase):
    """An arm a user adds for their own MCP server passes the self-test: the stand-in calls the MCP server the arm's tool
    sentence names, so ARM_<F>_USED=mcp sees the tool used."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_calls_the_named_mcp_server(self):
        out = self.t / "out" / "brief.md"; out.parent.mkdir()
        prompt = (f"Add a reminder.\n\nExplore this change with the docs search (the `docsearch` MCP server) along with "
                  f"your other tools. Write the brief to {out}")
        r = run([str(STAND / "selftest" / "bin" / "claude"), "-p", prompt, "--output-format", "stream-json"], cwd=self.t)
        names = [c["name"] for e in map(json.loads, r.stdout.splitlines()) if e["type"] == "assistant"
                 for c in e["message"]["content"]]
        self.assertTrue(any(n.startswith("mcp__docsearch__") for n in names), names)


class Marketplace(unittest.TestCase):
    """The kit's repository is its own marketplace: `claude plugin marketplace add <repo>` finds the plugin at the root, and
    the install line the README gives (<plugin>@<marketplace>) names both correctly."""

    def test_marketplace_lists_the_plugin_at_the_root(self):
        listed = dict((d, s) for s, d in export.manifest())
        self.assertIn(".claude-plugin/marketplace.json", listed)
        market = json.loads((STAND / listed[".claude-plugin/marketplace.json"]).read_text())
        plugin = json.loads((STAND / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual([(p["name"], p["source"]) for p in market["plugins"]], [(plugin["name"], "./")])
        readme = (STAND / listed["README.md"]).read_text()
        self.assertIn(f"claude plugin install {plugin['name']}@{market['name']}", readme)


class ReadmeOpening(unittest.TestCase):
    """The README opens with what the kit does and, right after, why it matters, with a link to the study."""

    def test_what_then_why(self):
        readme = (STAND / "KIT_README.md").read_text()
        heads = [l for l in readme.splitlines() if l.startswith("## ")]
        self.assertEqual(heads[:2], ["## What it does", "## Why it matters"])
        why = readme.split("## Why it matters", 1)[1].split("\n## ", 1)[0]
        self.assertIn("https://articles.segmently.ai/coding-agents-project-rules", why)
        self.assertIn("https://github.com/segmently-ai/segmently-modules-plugins", why)   # where the studied tool lives


class ManifestExclusion(unittest.TestCase):
    """A manifest line "!<glob>" keeps matching files out of the kit even when an earlier glob lists them: a stand-local
    file next to the public ones never leaves the repository."""

    def test_exclusion_drops_globbed_files(self):
        t = Path(tempfile.mkdtemp())
        try:
            (t / "tests").mkdir()
            for f in ("test_a.py", "test_local.py"):
                (t / "tests" / f).write_text("")
            got = export.manifest(["tests/*.py", "!tests/test_local.py"], root=t)
            self.assertEqual(got, [("tests/test_a.py", "tests/test_a.py")])
        finally:
            shutil.rmtree(t)

    def test_the_kit_holds_no_local_arm(self):
        """An arm whose adapter stays in the stand (not listed) leaves no file of its own in the kit."""
        listed = {d for _, d in export.manifest()}
        local = {p.stem.lower() for p in (STAND / "arms").glob("*.zsh")} - {Path(d).stem.lower() for d in listed
                                                                              if d.startswith("arms/")}
        self.assertFalse([d for d in listed if any(f in Path(d).name.lower() for f in local)],
                         "a stand-local arm's file is in the kit")
