import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, STANDIN, demo_repo, run, template, workspace

WS = STAND / "skills" / "context-recall" / "scripts" / "workspace.py"
CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


def pin(key):
    return re.search(rf"^{key}=(\S+)", template().read_text(), re.M).group(1)


class ArmCards(unittest.TestCase):
    """The user picks the arms from cards: each says what the tool is and, when this machine lacks what it needs, the
    install it will take. The agent alone (BARE) needs nothing and is always in."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)
        self.bin = self.t / "bin"; self.bin.mkdir()

    def tearDown(self):
        shutil.rmtree(self.t)

    def fake(self, *names):
        for n in names:
            (self.bin / n).write_text("#!/bin/sh\necho 0\n"); (self.bin / n).chmod(0o755)

    def cards(self):
        p = run(["python3", WS, "arms", "--repo", self.repo, "--json"],
                env={"PATH": f"{STANDIN}:{self.bin}:/usr/bin:/bin"})
        self.assertEqual(p.returncode, 0, p.stderr)
        return {c["family"]: c for c in json.loads(p.stdout)["arms"]}

    def test_nothing_installed(self):
        c = self.cards()
        self.assertEqual(c["BARE"]["status"], "ready")
        self.assertEqual(c["SERENA"]["status"], "needs")
        self.assertEqual(c["SERENA"]["missing"], ["uv"])
        self.assertEqual(c["TRAIL"]["missing"], ["npm"])
        for f in c.values():
            self.assertTrue(f["about"])

    def test_uv_present_tool_missing(self):
        self.fake("uv")
        c = self.cards()
        self.assertEqual(c["SERENA"]["status"], "install")
        self.assertIn(f"uv tool install serena-agent=={pin('SERENA_VERSION')}", c["SERENA"]["install"])
        self.assertIn(f"uv tool install graphifyy=={pin('GRAPHIFY_VERSION')}", c["GRAPHIFY"]["install"])

    def test_tool_present(self):
        self.fake("uv", "serena")
        self.assertEqual(self.cards()["SERENA"]["status"], "ready")

    def test_npm_present_trail_installed_by_setup(self):
        self.fake("npm")
        c = self.cards()["TRAIL"]
        self.assertEqual(c["status"], "install")
        self.assertIn("setup", c["install"])

    def test_text_cards_name_the_install(self):
        p = run(["python3", WS, "arms", "--repo", self.repo], env={"PATH": f"{STANDIN}:{self.bin}:/usr/bin:/bin"})
        self.assertRegex(p.stdout, r"SERENA.*\n.*needs uv")


class ArmChoice(unittest.TestCase):
    """init writes the arms the user chose (the agent alone by default); arms --set changes them later."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)

    def tearDown(self):
        shutil.rmtree(self.t)

    def arms_line(self):
        return re.search(r"^ARMS=(.*)$", (self.repo / ".context-recall" / "stand.env").read_text(), re.M).group(1)

    def test_default_is_the_agent_alone(self):
        self.assertEqual(run(["python3", WS, "init", "--repo", self.repo]).returncode, 0)
        self.assertEqual(self.arms_line(), "BARE")

    def test_init_with_chosen_arms(self):
        p = run(["python3", WS, "init", "--repo", self.repo, "--arms", "TRAIL,SERENA"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.arms_line(), "BARE,TRAIL,SERENA")

    def test_unknown_arm_refused(self):
        p = run(["python3", WS, "init", "--repo", self.repo, "--arms", "NOPE"])
        self.assertEqual(p.returncode, 2)
        self.assertIn("NOPE", p.stderr)
        self.assertFalse((self.repo / ".context-recall").exists())

    def test_set_later(self):
        run(["python3", WS, "init", "--repo", self.repo])
        p = run(["python3", WS, "arms", "--repo", self.repo, "--set", "GRAPHIFY"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.arms_line(), "BARE,GRAPHIFY")


class AddArmLater(unittest.TestCase):
    """An arm added to a label's cases later runs only its own sessions: the earlier sessions keep their verdicts and are
    not judged (paid for) again."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        shutil.copy(CASE, self.ws / "cases")
        self.env = {"BENCH_WORKSPACE": str(self.ws), "RUN_LABEL": "a"}

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_resume_with_a_new_arm(self):
        p = run([STAND / "bench.sh", "case", "d01", "--clean"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout[-800:] + p.stderr[-800:])
        v = self.t / "data" / "runs" / "a" / "d01" / "out" / "BARE-1" / "verdict.json"
        before = v.stat().st_mtime_ns
        p = run([STAND / "bench.sh", "case", "d01", "--clean", "--resume"], env=dict(self.env, ARMS="BARE,BARE-b"))
        self.assertEqual(p.returncode, 0, p.stdout[-800:] + p.stderr[-800:])
        self.assertEqual(v.stat().st_mtime_ns, before, "the earlier session was judged again")
        briefs = self.ws / "results" / "a" / "d01" / "briefs"
        self.assertTrue((briefs / "BARE-b-1.verdict.json").exists())
        self.assertTrue((briefs / "BARE-1.verdict.json").exists())
