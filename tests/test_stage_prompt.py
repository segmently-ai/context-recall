import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class StagePrompt(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.ws = workspace(self.t, demo_repo(self.t))
        (self.ws / "cases").mkdir()
        self.env = {"BENCH_WORKSPACE": str(self.ws), "BENCH": str(self.t / "runs")}

    def tearDown(self):
        shutil.rmtree(self.t)

    def session(self, **changes):
        """case2task, prep of the BARE clone, one stand-in session; returns the session's out dir."""
        c = json.loads(CASE.read_text()); c.update(changes)
        f = self.ws / "cases" / "d01-x.case.json"; f.write_text(json.dumps(c))
        for cmd in (["python3", STAND / "case2task.py", f, "d01"], [STAND / "prep.sh", "d01", "d01-before", "BARE"],
                    [STAND / "run.sh", "d01", "BARE", "1", self.ws / "tasks" / "d01.request.txt"]):
            p = run(cmd, env=self.env)
            self.assertEqual(p.returncode, 0, p.stdout[-500:] + p.stderr[-500:])
        return self.t / "runs" / "d01" / "out" / "BARE-1"

    def test_task_prompt_has_input_and_template(self):
        out = self.session(stage="task", inputs=[{"label": "Task", "original": "o", "text": "Add an extension endpoint."}])
        prompt = (out / "prompt.txt").read_text()
        self.assertIn("## Task\nAdd an extension endpoint.", prompt)
        self.assertIn("write a brief for whoever will implement this task", prompt)
        self.assertTrue((out / "TEMPLATE.md").read_text().startswith("# Brief for the task"))

    def test_spec_template_keeps_the_scored_sections(self):
        text = (STAND / "templates" / "spec.md").read_text()
        self.assertIn("## 1. Files to change", text)
        self.assertIn("## 3. Rules and constraints", text)

    def test_brief_prompt_unchanged(self):
        out = self.session()
        self.assertIn("write a brief for whoever will plan it to", (out / "prompt.txt").read_text())
        self.assertEqual((out / "TEMPLATE.md").read_text(), (STAND / "TEMPLATE.md").read_text())
