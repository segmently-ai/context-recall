import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class Seed(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        self.env = {"BENCH_WORKSPACE": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.t)

    def request(self, case: dict) -> str:
        f = self.ws / "cases" / "d01-x.case.json"
        f.write_text(json.dumps(case))
        p = run(["python3", STAND / "case2task.py", f, "d01"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return (self.ws / "tasks" / "d01.request.txt").read_text()

    def test_seed_in_request(self):
        c = json.loads(CASE.read_text())
        c["seed"] = {"text": "It is in the reservations service.", "paths": ["docs/reservations.md"]}
        req = self.request(c)
        self.assertTrue(json.loads((self.ws / "tasks" / "d01.truth.json").read_text())["seeded"])
        self.assertTrue(req.startswith(c["request_en"].strip() + "\n\nWhat the operator already knows:\n"))
        self.assertIn("It is in the reservations service.\n- docs/reservations.md\n", req)

    def test_seed_path_missing_warned(self):
        c = json.loads(CASE.read_text())
        c["seed"] = {"text": "", "paths": ["docs/reservations.md", "docs/nowhere.md"]}
        f = self.ws / "cases" / "d01-x.case.json"
        f.write_text(json.dumps(c))
        p = run(["python3", STAND / "validate_case.py", f], env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("seed path not at the snapshot: docs/nowhere.md", p.stdout)
        self.assertNotIn("docs/reservations.md", p.stdout.split("seed path")[-1] if "seed path" in p.stdout else "")

    def test_no_seed_request_unchanged(self):
        c = json.loads(CASE.read_text())
        self.assertEqual(self.request(c), c["request_en"].strip() + "\n")
