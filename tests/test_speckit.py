import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run

ID = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
      "GIT_COMMITTER_EMAIL": "t@example.com"}
SPEC = '# Feature Specification: Extend a booking\n\n**Input**: User description: "Let members extend their bookings."\n\n## Scenarios\n'
TASKS = ("# Tasks\n\n- [ ] T001 [P] Add extend in src/reservations/service.js\n"
         "- [ ] **T002:** Add the handler\n  - [ ] T002.1: wire it in src/api/handlers.js\n")


def git(r, *a):
    p = run(["git", "-C", r, *a], env=ID)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


class SpecKit(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp()); r = self.r = self.t / "repo"
        (r / "specs" / "001-extend").mkdir(parents=True); (r / "src" / "reservations").mkdir(parents=True)
        (r / "src" / "api").mkdir(parents=True)
        git(r, "init", "-q")
        (r / "specs/001-extend/spec.md").write_text(SPEC); (r / "specs/001-extend/plan.md").write_text("# Plan\nTwo steps.\n")
        (r / "specs/001-extend/tasks.md").write_text(TASKS)
        git(r, "add", "-A"); git(r, "commit", "-qm", "spec")
        (r / "src/reservations/service.js").write_text("x\n"); git(r, "add", "-A"); git(r, "commit", "-qm", "service")
        self.c1 = git(r, "rev-parse", "HEAD")
        (r / "src/api/handlers.js").write_text("y\n"); git(r, "add", "-A"); git(r, "commit", "-qm", "handler")
        self.c2 = git(r, "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_oldest_commits_first(self):
        for k in range(3):
            (self.r / "src/reservations/service.js").write_text(f"later {k}\n"); git(self.r, "commit", "-qam", f"later {k}")
        out = self.t / "features"
        run(["python3", STAND / "history" / "speckit.py", "--repo", self.r, "--out", out, "--max-commits", "1"])
        f = json.loads((out / "001-extend" / "feature.json").read_text())
        self.assertEqual(f["tasks"][0]["commits"], [self.c1])

    def test_tasks_without_paths_fall_back_to_commits_after_the_spec(self):
        (self.r / "specs/001-extend/tasks.md").write_text("- [ ] **T001:** Add extend to the service\n")
        git(self.r, "commit", "-qam", "tasks reworded")   # a specs-only commit is not a candidate
        (self.r / "src/api/handlers.js").write_text("z\n"); git(self.r, "commit", "-qam", "more")
        c3 = git(self.r, "rev-parse", "HEAD")
        out = self.t / "features"
        run(["python3", STAND / "history" / "speckit.py", "--repo", self.r, "--out", out])
        f = json.loads((out / "001-extend" / "feature.json").read_text())
        self.assertEqual(f["tasks"][0]["files"], [])
        self.assertEqual(f["commits"], [self.c1, self.c2, c3])

    def test_feature_json(self):
        out = self.t / "features"
        p = run(["python3", STAND / "history" / "speckit.py", "--repo", self.r, "--out", out])
        self.assertEqual(p.returncode, 0, p.stderr)
        f = json.loads((out / "001-extend" / "feature.json").read_text())
        self.assertEqual(f["request"], "Let members extend their bookings.")
        self.assertIn("Two steps.", f["architecture"]["text"])
        self.assertEqual([t["id"] for t in f["tasks"]], ["T001", "T002"])
        self.assertEqual(f["tasks"][1]["files"], ["src/api/handlers.js"])
        self.assertEqual(f["tasks"][0]["commits"], [self.c1])
        self.assertEqual(f["commits"], [self.c1, self.c2])
