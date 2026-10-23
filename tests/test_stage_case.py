import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"
INPUT = {"label": "Task", "original": "Add ReservationService.extend in src/reservations/service.js.",
         "text": "Let a member extend their own booking to a later end time."}


class StageCase(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        self.env = {"BENCH_WORKSPACE": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.t)

    def write(self, **changes):
        c = json.loads(CASE.read_text()); c.update(changes)
        f = self.ws / "cases" / "d01-x.case.json"; f.write_text(json.dumps(c))
        return f

    def truth(self, f):
        p = run(["python3", STAND / "case2task.py", f, "d01"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads((self.ws / "tasks" / "d01.truth.json").read_text())

    def validate(self, f):
        return run(["python3", STAND / "validate_case.py", f], env=self.env)

    def test_stage_written(self):
        given = [{"rule": "A slot is end-exclusive", "source": "docs/reservations.md:7", "why": "stated in the task"}]
        t = self.truth(self.write(stage="task", group="f01", inputs=[INPUT], given_rules=given))
        self.assertEqual((t["stage"], t["group"]), ("task", "f01"))
        self.assertEqual(t["inputs"], [{"label": "Task", "text": INPUT["text"]}])
        self.assertEqual(t["given_rules"], [{"rule": "A slot is end-exclusive", "source": "docs/reservations.md:7"}])

    def test_brief_unchanged(self):
        t = self.truth(self.write())
        self.assertFalse({"stage", "group", "inputs", "given_rules"} & set(t))

    def test_inputs_required(self):
        p = self.validate(self.write(stage="architecture"))
        self.assertEqual(p.returncode, 1)
        self.assertIn("needs inputs", p.stdout)

    def test_unknown_stage_refused(self):
        p = self.validate(self.write(stage="deploy"))
        self.assertEqual(p.returncode, 1)
        self.assertIn("stage", p.stdout)

    def test_input_hint_warned(self):
        hinted = dict(INPUT, text=INPUT["original"])
        p = self.validate(self.write(stage="task", inputs=[hinted]))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("an input names a file of the change: service.js", p.stdout)

    def test_given_rule_source_checked(self):
        given = [{"rule": "x", "source": "docs/nowhere.md:3", "why": "y"}]
        p = self.validate(self.write(stage="task", inputs=[INPUT], given_rules=given))
        self.assertEqual(p.returncode, 1)
        self.assertIn("given rule 1: docs/nowhere.md is not in the snapshot", p.stdout)
