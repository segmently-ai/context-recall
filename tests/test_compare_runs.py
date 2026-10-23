import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run, workspace


def verdict(**v):
    return {"must_know": [{"id": k, "verdict": x} for k, x in v.items()], "extra_rules": [], "unsupported": []}


class CompareRuns(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, self.t)
        (self.ws / "tasks").mkdir()
        for c in ("c1", "c2"):
            (self.ws / "tasks" / f"{c}.truth.json").write_text(json.dumps({"rules": [{"id": "F1"}, {"id": "F2"}]}))
        self.env = {"BENCH_WORKSPACE": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.t)

    def put(self, label, case, v, key="documented", patch=""):
        b = self.ws / "results" / label / case / "briefs"
        b.mkdir(parents=True, exist_ok=True)
        (b / "BARE-1.score.json").write_text(json.dumps({"cost_usd": 0.1, "rules": []}))
        (b / "BARE-1.verdict.json").write_text(json.dumps(v))
        (b.parent / "stand.json").write_text(json.dumps({"key": key, "arms": ["BARE"], "docs_patch": patch}))

    def compare(self, *extra):
        return run(["python3", STAND / "compare_runs.py", "A", "B", "--draws", "200", *extra], env=self.env)

    def test_gain_and_loss_listed(self):
        self.put("A", "c1", verdict(F1="provided", F2="absent")); self.put("B", "c1", verdict(F1="absent", F2="provided"))
        p = self.compare("c1")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("c1 BARE: gained F2; lost F1", p.stdout)

    def test_mixed_key_refused(self):
        self.put("A", "c1", verdict(F1="provided")); self.put("B", "c1", verdict(F1="provided"), key="all")
        p = self.compare("c1")
        self.assertEqual(p.returncode, 2)
        self.assertIn("key", p.stderr)

    def test_case_edited_between_labels_refused(self):   # shifted rule ids would read as gained and lost
        for label, text in (("A", "a slot is end-exclusive"), ("B", "an extension stops at the next booking")):
            (self.ws / "tasks" / label).mkdir()
            (self.ws / "tasks" / label / "c1.truth.json").write_text(
                json.dumps({"snapshot": "s1", "rules": [{"id": "F1", "rule": text}, {"id": "F2", "rule": "y"}]}))
        self.put("A", "c1", verdict(F1="provided")); self.put("B", "c1", verdict(F1="provided"))
        p = self.compare("c1")
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("truth", p.stderr)

    def test_label_mixing_patches_refused(self):   # one run is one state of the docs
        for c, patch in (("c1", "p1"), ("c2", "p2")):
            self.put("A", c, verdict(F1="provided"), patch=patch); self.put("B", c, verdict(F1="provided"))
        p = self.compare()
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn("docs patch", p.stderr)

    def test_excluded_case_left_out(self):
        for c in ("c1", "c2"):
            self.put("A", c, verdict(F1="absent", F2="absent")); self.put("B", c, verdict(F1="provided", F2="absent"))
        (self.ws / "results" / "B" / "c2" / "excluded.txt").write_text("the docs patch did not apply\n")
        p = self.compare()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Left out: c2 (B: the docs patch did not apply)", p.stdout)
        self.assertIn("| BARE | 1 |", p.stdout)
