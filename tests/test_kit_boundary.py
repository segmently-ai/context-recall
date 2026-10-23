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
