import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run

WS = STAND / "skills" / "context-recall" / "scripts" / "workspace.py"
CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class OwnArm(unittest.TestCase):
    """The user's own tool becomes an arm without touching the kit: add-arm writes its adapter and paragraph into the
    workspace (<repo>/.context-recall/arms/), from three answers — what kind it is (a Claude Code plugin with a skill, an
    MCP server, a CLI), how it is reached, what it is called. The kit then runs, scores and lists it like its own arms."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)
        self.assertEqual(run(["python3", WS, "init", "--repo", self.repo]).returncode, 0)
        self.ws = self.repo / ".context-recall"
        self.plugin = self.t / "my-discovery"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "my-discovery", "version": "1.2.0"}')
        (self.plugin / "skills" / "discover").mkdir(parents=True)
        (self.plugin / "skills" / "discover" / "SKILL.md").write_text("---\nname: discover\n---\n")

    def tearDown(self):
        shutil.rmtree(self.t)

    def add(self, *args):
        return run(["python3", WS, "add-arm", "--repo", self.repo, *args])

    def case(self, arms):
        self.assertEqual(run(["python3", WS, "arms", "--repo", self.repo, "--set", arms]).returncode, 0)
        shutil.copy(CASE, self.ws / "cases")
        env = {"BENCH_WORKSPACE": str(self.ws), "BENCH_DATA": str(self.t / "data"), "RUNS": "1"}
        p = run([STAND / "bench.sh", "case", "d01"], env=env)
        self.assertEqual(p.returncode, 0, p.stdout[-800:] + p.stderr[-800:])
        return self.ws / "results" / "d01" / "briefs"

    def test_plugin_arm_written_to_the_workspace(self):
        p = self.add("--name", "discover", "--kind", "plugin", "--plugin", self.plugin, "--skill", "discover")
        self.assertEqual(p.returncode, 0, p.stderr)
        a = (self.ws / "arms" / "DISCOVER.zsh").read_text()
        self.assertIn("ARM_DISCOVER_USED='skill'", a)
        self.assertIn("--plugin-dir", a)
        self.assertTrue((self.ws / "arms" / "integration-DISCOVER.md").read_text().strip())
        self.assertIn("arms --repo", p.stdout)   # the next step is printed
        self.assertFalse(list((STAND / "arms").glob("DISCOVER*")), "the kit itself was written to")

    def test_own_arm_on_the_cards(self):
        self.add("--name", "DISCOVER", "--kind", "plugin", "--plugin", self.plugin, "--skill", "discover")
        cards = {c["family"]: c for c in json.loads(run(["python3", WS, "arms", "--repo", self.repo, "--json"]).stdout)["arms"]}
        self.assertTrue(cards["DISCOVER"]["own"])
        self.assertEqual(cards["DISCOVER"]["status"], "ready")
        self.assertFalse(cards["BARE"]["own"])

    def test_refusals(self):
        for args, why in ((["--name", "BARE", "--kind", "cli", "--cli", "x"], "BARE"),
                          (["--name", "MY-TOOL", "--kind", "cli", "--cli", "x"], "MY-TOOL"),
                          (["--name", "X", "--kind", "plugin", "--plugin", self.t, "--skill", "s"], "plugin.json"),
                          (["--name", "X", "--kind", "plugin", "--plugin", self.plugin, "--skill", "nope"], "nope")):
            with self.subTest(args=args):
                p = self.add(*args)
                self.assertEqual(p.returncode, 2, p.stdout)
                self.assertIn(why, p.stderr)
        self.assertFalse((self.ws / "arms").exists() and list((self.ws / "arms").iterdir()))

    def test_replace_points_the_arm_at_a_new_version(self):   # a plugin update moves its cache folder
        self.add("--name", "DISCOVER", "--kind", "plugin", "--plugin", self.plugin, "--skill", "discover")
        new = self.t / "my-discovery-2"; shutil.copytree(self.plugin, new)
        self.assertEqual(self.add("--name", "DISCOVER", "--kind", "plugin", "--plugin", new, "--skill", "discover").returncode, 2)
        p = self.add("--name", "DISCOVER", "--kind", "plugin", "--plugin", new, "--skill", "discover", "--replace")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(str(new.resolve()), (self.ws / "arms" / "DISCOVER.zsh").read_text())
        p = self.add("--name", "BARE", "--kind", "cli", "--cli", "x", "--replace")   # never a kit arm
        self.assertEqual(p.returncode, 2)

    def test_installed_plugin_by_its_id(self):   # the user names the plugin as Claude Code does; its current folder is found
        cfg = self.t / "cfg"; (cfg / "plugins").mkdir(parents=True)
        (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "my-discovery@my-market": [{"scope": "user", "installPath": str(self.plugin), "version": "1.2.0"}]}}))
        p = run(["python3", WS, "add-arm", "--repo", self.repo, "--name", "DISCOVER", "--kind", "plugin",
                 "--plugin", "my-discovery@my-market", "--skill", "discover"], env={"CLAUDE_CONFIG_DIR": str(cfg)})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(str(self.plugin.resolve()), (self.ws / "arms" / "DISCOVER.zsh").read_text())
        p = run(["python3", WS, "add-arm", "--repo", self.repo, "--name", "OTHER", "--kind", "plugin",
                 "--plugin", "nope@my-market", "--skill", "discover"], env={"CLAUDE_CONFIG_DIR": str(cfg)})
        self.assertEqual(p.returncode, 2)
        self.assertIn("my-discovery@my-market", p.stderr)   # the installed ids are listed

    def test_help_names_the_workspace(self):
        p = run(["python3", WS, "--help"])
        self.assertIn("git-ignored by its own .gitignore", " ".join(p.stdout.split()))

    def test_plugin_arm_runs_and_counts_as_used(self):
        self.add("--name", "DISCOVER", "--kind", "plugin", "--plugin", self.plugin, "--skill", "discover")
        briefs = self.case("DISCOVER")
        s = json.loads((briefs / "DISCOVER-1.score.json").read_text())
        self.assertTrue(s["tool_used"])
        self.assertTrue((briefs / "DISCOVER-1.verdict.json").exists())

    def test_mcp_arm_runs_and_counts_as_used(self):
        self.add("--name", "DOCS", "--kind", "mcp", "--command", "/bin/cat")
        s = json.loads((self.case("DOCS") / "DOCS-1.score.json").read_text())
        self.assertTrue(s["tool_used"])

    def test_cli_arm_runs_and_counts_as_used(self):
        self.add("--name", "MAPPER", "--kind", "cli", "--cli", "mapper", "--index", "touch .mapper-index")
        s = json.loads((self.case("MAPPER") / "MAPPER-1.score.json").read_text())
        self.assertTrue(s["tool_used"])
        self.assertIn("cli", (self.ws / "arms" / "MAPPER.zsh").read_text())
        self.assertTrue(re.search(r"touch \.mapper-index", (self.ws / "arms" / "MAPPER.zsh").read_text()))
