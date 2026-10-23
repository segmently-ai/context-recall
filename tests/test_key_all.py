import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class KeyAll(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        shutil.copy(CASE, self.ws / "cases")
        self.env = {"BENCH_WORKSPACE": str(self.ws), "BENCH": str(self.t / "runs")}

    def tearDown(self):
        shutil.rmtree(self.t)

    def truth(self, **env):
        p = run(["python3", STAND / "case2task.py", self.ws / "cases" / CASE.name, "d01"], env=dict(self.env, **env))
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads((self.ws / "tasks" / "d01.truth.json").read_text())

    def judge_input(self, **env):
        self.truth(**env)
        self.assertEqual(run([STAND / "prep.sh", "d01", "d01-before", "BARE"], env=self.env).returncode, 0)
        out = self.t / "runs" / "d01" / "out" / "BARE-1"; out.mkdir(parents=True)
        (out / "brief.md").write_text("# Brief\n\n## 3. Rules and constraints\n- none\n")
        run([STAND / "judge.sh", "d01", "BARE-1"], env=dict(self.env, **env))
        return (out / "judge-input.md").read_text()

    def test_key_all_adds_undocumented(self):
        u = [r for r in self.truth(KEY="all")["rules"] if r["id"].startswith("U")]
        self.assertEqual([r["id"] for r in u], ["U1"])
        self.assertEqual(u[0]["rule"], "A cancelled booking cannot be extended")
        self.assertEqual(u[0]["sources"], [])

    def test_key_unset_no_undocumented(self):
        self.assertFalse([r for r in self.truth()["rules"] if r["id"].startswith("U")])

    def test_judge_told_about_rules_without_a_source(self):
        text = self.judge_input(KEY="all")
        self.assertIn("- U1: A cancelled booking cannot be extended — source: none (not written in any doc at the snapshot)", text)
        self.assertIn("A rule with no source", text)

    def test_judge_input_unchanged_without_key(self):
        self.assertNotIn("A rule with no source", self.judge_input())
