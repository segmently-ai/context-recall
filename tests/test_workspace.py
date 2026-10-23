import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

CASE = STAND / "selftest" / "cases" / "d01-extend-booking.case.json"


class Workspace(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)
        self.ws = workspace(self.t, self.repo)
        (self.ws / "cases").mkdir()
        shutil.copy(CASE, self.ws / "cases")
        self.env = {"BENCH_WORKSPACE": str(self.ws)}

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_case2task_writes_into_workspace(self):
        p = run(["python3", STAND / "case2task.py", self.ws / "cases" / CASE.name, "d01"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((self.ws / "tasks" / "d01.truth.json").exists())
        self.assertFalse((STAND / "tasks" / "d01.truth.json").exists())

    def test_status_lists_workspace_cases(self):
        p = run([STAND / "bench.sh", "status"], env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("d01-extend-booking", p.stdout)

    def test_unknown_case_refused(self):
        p = run([STAND / "bench.sh", "case", "d99"], env=self.env)
        self.assertEqual(p.returncode, 2)
        self.assertIn("no single case file for d99", p.stderr)
        self.assertNotIn("rejected", p.stderr)

    def test_whitespace_value_in_stand_env_refused(self):
        env_file = self.ws / "stand.env"
        env_file.write_text(env_file.read_text().replace(f"HOST_REPO={self.repo}", f"HOST_REPO={self.t}/sp ace/repo"))
        for cmd in ([STAND / "bench.sh", "status"], ["python3", STAND / "stats.py"]):
            p = run(cmd, env=self.env)
            self.assertEqual(p.returncode, 2, cmd)
            self.assertIn("HOST_REPO", p.stderr)

    def test_comment_after_a_value_allowed(self):
        env_file = self.ws / "stand.env"
        env_file.write_text(env_file.read_text().replace("RUNS=1", "RUNS=1   # one session per arm"))
        self.assertEqual(run([STAND / "bench.sh", "status"], env=self.env).returncode, 0)

    def test_unknown_snapshot_refused(self):
        c = (self.ws / "cases" / CASE.name)
        c.write_text(c.read_text().replace('"snapshot": "d01-before"', '"snapshot": "nosuchref"'))
        p = run([STAND / "bench.sh", "case", "d01"], env=self.env)
        self.assertEqual(p.returncode, 2)
        self.assertIn("nosuchref", p.stderr)

    def test_case_without_rules_refused(self):
        c = (self.ws / "cases" / CASE.name)
        c.write_text(c.read_text().replace('docs/reservations.md:', 'docs/nowhere.md:').replace('docs/audit.md:', 'docs/nowhere.md:')
                     .replace('docs/api.md:', 'docs/nowhere.md:'))
        p = run(["python3", STAND / "case2task.py", c, "d01"], env=self.env)
        self.assertEqual(p.returncode, 2)
        self.assertIn("no rule", p.stderr)

    def test_whitespace_path_refused(self):
        spaced = self.t / "my ws"
        shutil.copytree(self.ws, spaced)
        p = run([STAND / "bench.sh", "status"], env={"BENCH_WORKSPACE": str(spaced)})
        self.assertEqual(p.returncode, 2)
        self.assertIn("BENCH_WORKSPACE", p.stderr)
