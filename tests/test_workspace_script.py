import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run

WS = STAND / "skills" / "context-recall" / "scripts" / "workspace.py"
GIT_ID = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
          "GIT_COMMITTER_EMAIL": "t@example.com"}


class WorkspaceScript(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)

    def tearDown(self):
        shutil.rmtree(self.t)

    def ws(self, *args):
        return run(["python3", WS, *args])

    def test_init_keeps_repo_clean(self):
        p = self.ws("init", "--repo", self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)
        w = self.repo / ".context-recall"
        self.assertIn(f"HOST_REPO={self.repo.resolve()}", (w / "stand.env").read_text())
        self.assertTrue((w / "cases").is_dir() and (w / "prereg").is_dir())
        self.assertEqual(json.loads((w / "state.json").read_text())["phase"], "selftest")
        self.assertEqual(run(["git", "-C", self.repo, "status", "--porcelain"]).stdout, "")

    def test_detect_none(self):
        bare = self.t / "bare"; bare.mkdir()
        run(["git", "-C", bare, "init", "-q"]); (bare / "a.js").write_text("1\n")
        run(["git", "-C", bare, "add", "-A"]); run(["git", "-C", bare, "commit", "-qm", "feat: a"], env=GIT_ID)
        p = self.ws("detect", "--repo", bare)
        self.assertEqual(p.returncode, 3)
        self.assertIn("no task history", p.stdout)

    def test_detect_taskfiles(self):   # the demo writes a task file before each task
        p = self.ws("detect", "--repo", self.repo, "--json")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        found = json.loads(p.stdout)["sources"]
        self.assertEqual(found[0]["source"], "taskfiles")
        self.assertEqual(found[0]["globs"], ["tasks/*.md"])

    def test_detect_two_folders(self):   # one glob per folder, never a glob over every doc of the repository
        (self.repo / "notes").mkdir(); (self.repo / "notes" / "n.md").write_text("## Run\n\nA note task.\n")
        run(["git", "-C", self.repo, "add", "-A"]); run(["git", "-C", self.repo, "commit", "-qm", "note"], env=GIT_ID)
        found = json.loads(self.ws("detect", "--repo", self.repo, "--json").stdout)["sources"]
        self.assertEqual(found[0]["globs"], ["notes/*.md", "tasks/*.md"])

    def test_status_and_phase(self):
        self.ws("init", "--repo", self.repo)
        self.assertIn("selftest", self.ws("status", "--repo", self.repo).stdout)
        self.assertEqual(self.ws("phase", "configure", "--repo", self.repo).returncode, 0)
        self.assertIn("configure", self.ws("status", "--repo", self.repo).stdout)
        self.assertEqual(self.ws("phase", "nonsense", "--repo", self.repo).returncode, 2)

    def test_status_shows_disk_evidence(self):
        self.ws("init", "--repo", self.repo)
        w = self.repo / ".context-recall"
        for c in ("d01-extend-booking", "d02-cancel-mail"):
            shutil.copy(STAND / "selftest" / "cases" / f"{c}.case.json", w / "cases")
        (w / "prereg" / "2026-10-23.md").write_text("Question …\n")
        (w / "results" / "pilot" / "d01").mkdir(parents=True)
        (w / "results" / "pilot" / "d01" / "summary.md").write_text("# Case d01\n")
        out = self.ws("status", "--repo", self.repo).stdout
        self.assertIn("cases: 2", out)
        self.assertIn("prereg: 2026-10-23.md", out)
        self.assertIn("results: pilot (1 case)", out)

    def test_init_refuses_whitespace_path(self):
        spaced = self.t / "my repo"
        shutil.copytree(self.repo, spaced)
        p = self.ws("init", "--repo", spaced)
        self.assertEqual(p.returncode, 2)
        self.assertIn("whitespace", p.stderr)
