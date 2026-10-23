import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class RunLabels(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        shutil.copy(CASE, self.ws / "cases")
        self.env = {"BENCH_WORKSPACE": str(self.ws), "RUN_LABEL": "a"}

    def tearDown(self):
        shutil.rmtree(self.t)

    def case(self, *flags):
        return run([STAND / "bench.sh", "case", "d01", "--clean", *flags], env=self.env)

    def test_label_paths(self):
        p = self.case()
        self.assertEqual(p.returncode, 0, p.stdout[-800:] + p.stderr[-800:])
        self.assertTrue((self.ws / "results" / "a" / "d01" / "summary.md").exists())
        self.assertTrue((self.t / "data" / "runs" / "a" / "d01" / "out" / "BARE-1").is_dir())

    def test_existing_label_refused(self):
        self.assertEqual(self.case().returncode, 0)
        p = self.case()
        self.assertEqual(p.returncode, 2)
        self.assertIn("--resume", p.stderr)

    def test_resume_allowed(self):
        self.assertEqual(self.case().returncode, 0)
        self.assertEqual(self.case("--resume").returncode, 0)

    def test_resume_with_another_key_refused(self):   # its earlier sessions were judged against the other key
        self.assertEqual(self.case().returncode, 0)
        p = run([STAND / "bench.sh", "case", "d01", "--clean", "--resume"], env=dict(self.env, KEY="all"))
        self.assertEqual(p.returncode, 2, p.stdout[-500:] + p.stderr[-500:])
        self.assertIn("KEY", p.stderr)
        rules = json.loads((self.ws / "tasks" / "a" / "d01.truth.json").read_text())["rules"]
        self.assertNotIn("U1", [r["id"] for r in rules])

    def test_label_under_an_explicit_bench(self):
        env = dict(self.env, BENCH=str(self.t / "myruns"))
        p = run([STAND / "bench.sh", "case", "d01", "--clean"], env=env)
        self.assertEqual(p.returncode, 0, p.stdout[-500:] + p.stderr[-500:])
        self.assertTrue((self.t / "myruns" / "a" / "d01" / "out" / "BARE-1").is_dir())
        p = run([STAND / "bench.sh", "case", "d01", "--clean"], env=dict(env, RUN_LABEL="b"))
        self.assertEqual(p.returncode, 0, p.stderr[-500:])

    def test_truth_per_label(self):   # a run's key is frozen with the run: another label's KEY never rewrites it
        self.assertEqual(self.case().returncode, 0)
        self.assertEqual(run([STAND / "bench.sh", "case", "d01", "--clean"], env=dict(self.env, RUN_LABEL="b", KEY="all")).returncode, 0)
        ids = lambda label: [r["id"] for r in json.loads((self.ws / "tasks" / label / "d01.truth.json").read_text())["rules"]]
        self.assertNotIn("U1", ids("a"))
        self.assertIn("U1", ids("b"))

    def test_bad_label_refused(self):
        p = run([STAND / "bench.sh", "status"], env={**self.env, "RUN_LABEL": "a/b"})
        self.assertEqual(p.returncode, 2)
        self.assertIn("RUN_LABEL", p.stderr)
