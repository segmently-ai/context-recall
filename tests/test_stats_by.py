import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run, workspace


class StatsBy(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, self.t)
        (self.ws / "tasks").mkdir()
        for cid, extra in (("c1", {"stage": "spec"}), ("c2", {"stage": "task", "seeded": True})):
            (self.ws / "tasks" / f"{cid}.truth.json").write_text(json.dumps({"rules": [{"id": "F1"}], **extra}))
            b = self.ws / "results" / cid / "briefs"; b.mkdir(parents=True)
            (b / "BARE-1.score.json").write_text(json.dumps({"rules": [{"id": "F1", "sighted": True}], "cost_usd": 0.1,
                                                            "duration_s": 5, "tool_used": True,
                                                            "files": {"code_recall_any": "1/1"}}))
            (b / "BARE-1.verdict.json").write_text(json.dumps({"must_know": [{"id": "F1", "verdict": "provided"}]}))
        self.env = {"BENCH_WORKSPACE": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.t)

    def stats(self, *a):
        p = run(["python3", STAND / "stats.py", "--draws", "100", *a, "c1", "c2"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_by_stage(self):
        out = self.stats("--by", "stage")
        self.assertIn("## Stage spec", out)
        self.assertIn("## Stage task", out)

    def test_by_seeded(self):
        out = self.stats("--by", "seeded")
        self.assertIn("## Seeded", out)
        self.assertIn("## Unseeded", out)

    def test_no_by_one_table(self):
        self.assertNotIn("## Stage", self.stats())
