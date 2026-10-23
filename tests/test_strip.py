import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class Strip(unittest.TestCase):
    """A snapshot that still holds the task's own text (its task file, the feature's spec) hands the answer to every arm:
    the case's strip list removes it from the base, and validate_case.py warns while it is there."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)
        self.ws = workspace(self.t, self.repo)
        (self.ws / "cases").mkdir()
        self.env = {"BENCH_WORKSPACE": str(self.ws), "BENCH": str(self.t / "runs")}

    def tearDown(self):
        shutil.rmtree(self.t)

    def write(self, **changes):
        c = json.loads(CASE.read_text()); c.pop("strip", None); c.update(changes)
        f = self.ws / "cases" / "d01-x.case.json"; f.write_text(json.dumps(c))
        return f

    def validate(self, f):
        return run(["python3", STAND / "validate_case.py", f], env=self.env)

    def test_request_in_snapshot_warned(self):
        p = self.validate(self.write())
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("the snapshot holds the request verbatim: tasks/d01.md", p.stdout)

    def test_stripped_file_not_warned(self):
        p = self.validate(self.write(strip=["tasks/d01.md"]))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn("holds the request", p.stdout)

    def test_input_original_in_snapshot_warned(self):
        spec = subprocess.run(["git", "-C", str(self.repo), "show", "d01-before:specs/001-extend-booking/spec.md"],
                              capture_output=True, text=True).stdout
        inp = {"label": "Spec", "original": spec, "text": "A member makes a booking longer, up to the next booking."}
        p = self.validate(self.write(stage="architecture", inputs=[inp], strip=["tasks/d01.md"]))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("the snapshot holds input 'Spec' verbatim: specs/001-extend-booking/spec.md", p.stdout)

    def test_strip_outside_the_snapshot_refused(self):
        p = self.validate(self.write(strip=["../elsewhere"]))
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("strip", p.stdout)

    def test_case_strip_removed_from_base(self):
        f = self.write(strip=["tasks/d01.md", "specs/001-extend-booking"])
        p = run(["python3", STAND / "case2task.py", f, "d01"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads((self.ws / "tasks" / "d01.truth.json").read_text())["strip"],
                         ["tasks/d01.md", "specs/001-extend-booking"])
        p = run([STAND / "prep.sh", "d01", "d01-before", "BARE"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        w = self.t / "runs" / "d01" / "BARE"
        self.assertFalse((w / "tasks" / "d01.md").exists())
        self.assertFalse((w / "specs" / "001-extend-booking").exists())
        self.assertTrue((w / "docs" / "reservations.md").exists())
