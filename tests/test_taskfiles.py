import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run

TASK_V1 = """Workflow: research first.

## Read

docs/api.md
- `src/api/handlers.js`

## Run

Fix the cancel form: it accepts an empty id.
"""
TASK_V2 = TASK_V1.replace("Fix the cancel form: it accepts an empty id.", "Show the café name — naïve sort ✓.")


def git(r, *a):
    p = run(["git", "-C", r, *a], env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                                      "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


class TaskFiles(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp()); r = self.r = self.t / "repo"
        (r / "tasks").mkdir(parents=True); (r / "src").mkdir(); (r / "docs").mkdir()
        git(r, "init", "-q")
        (r / "docs/api.md").write_text("# API\n"); (r / "tasks/form.md").write_text(TASK_V1)
        git(r, "add", "-A"); git(r, "commit", "-qm", "task v1")
        (r / "src/a.js").write_text("1\n"); git(r, "add", "-A"); git(r, "commit", "-qm", "fix form")
        self.fix1 = git(r, "rev-parse", "HEAD")
        (r / "tasks/form.md").write_text(TASK_V2); git(r, "commit", "-qam", "task v2")
        (r / "src/a.js").write_text("2\n"); git(r, "commit", "-qam", "name sort")
        self.fix2 = git(r, "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.t)

    def listing(self, *globs):
        g = [x for glob in (globs or ("tasks/*.md",)) for x in ("--glob", glob)]
        p = run(["python3", STAND / "history" / "taskfiles.py", "--repo", self.r, *g, "--json"])
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_lists_versions(self):
        out = self.listing()
        recs = out["records"]
        self.assertEqual(len(recs), 2)
        self.assertIn("accepts an empty id", recs[0]["request"])
        self.assertEqual(recs[0]["seed"]["paths"], ["docs/api.md", "src/api/handlers.js"])
        self.assertEqual(recs[0]["commits"], [self.fix1])
        self.assertEqual(recs[1]["commits"], [self.fix2])
        self.assertEqual(recs[0]["source"], "taskfiles")

    def test_commit_range_capped(self):
        more = []
        for k in range(4):
            (self.r / "src/a.js").write_text(f"x{k}\n"); git(self.r, "commit", "-qam", f"later {k}")
            more.append(git(self.r, "rev-parse", "HEAD"))
        # a git that logs its calls: the adapter must stop reading commits once it has enough (a large repository has
        # thousands after the last version of a task file)
        real, shim, log = shutil.which("git"), self.t / "shim", self.t / "calls.log"
        shim.mkdir(); (shim / "git").write_text(f'#!/bin/sh\necho "$@" >> {log}\nexec {real} "$@"\n'); (shim / "git").chmod(0o755)
        p = run(["python3", STAND / "history" / "taskfiles.py", "--repo", self.r, "--glob", "tasks/*.md", "--json",
                 "--max-commits", "2"], env={"PATH": f"{shim}:/usr/bin:/bin"})
        self.assertEqual(json.loads(p.stdout)["records"][1]["commits"], [self.fix2, more[0]])
        calls = log.read_text().splitlines()
        self.assertEqual([l for l in calls if "--name-only" in l and "--no-walk" not in l], [])   # one call per version
        self.assertEqual(len([l for l in calls if "--no-walk" in l]), 2)

    def test_other_task_file_commit_not_a_candidate(self):
        (self.r / "tasks/next.md").write_text("## Run\n\nThe next task.\n")
        git(self.r, "add", "-A"); git(self.r, "commit", "-qm", "next task written")
        (self.r / "src/a.js").write_text("3\n"); git(self.r, "commit", "-qam", "next task done")
        done = git(self.r, "rev-parse", "HEAD")
        form2 = [r for r in self.listing()["records"] if r["id"] == "form-2"][0]
        self.assertEqual(form2["commits"], [self.fix2, done])

    def test_utf8_and_untracked(self):
        (self.r / "tasks/new.md").write_text(TASK_V1)
        out = self.listing()
        self.assertIn("café", out["records"][1]["request"])
        self.assertEqual(out["skipped"], [{"path": "tasks/new.md", "reason": "untracked"}])

    def test_two_globs(self):   # task files in two folders: detect gives one glob per folder
        (self.r / "notes").mkdir(); (self.r / "notes/x.md").write_text("## Run\n\nA note task.\n")
        git(self.r, "add", "-A"); git(self.r, "commit", "-qm", "note task")
        (self.r / "src/a.js").write_text("n\n"); git(self.r, "commit", "-qam", "note task done")
        ids = [r["id"] for r in self.listing("tasks/*.md", "notes/*.md")["records"]]
        self.assertEqual(sorted(ids), ["form-1", "form-2", "x-1"])

    def test_broad_glob_keeps_a_docs_commit(self):   # a doc is no task file: its commit is a candidate, it is not listed
        (self.r / "docs/api.md").write_text("# API\n\nNames are sorted.\n"); git(self.r, "commit", "-qam", "docs: sorting")
        docs = git(self.r, "rev-parse", "HEAD")
        out = self.listing("**/*.md")
        form2 = [r for r in out["records"] if r["id"] == "form-2"][0]
        self.assertEqual(form2["commits"], [self.fix2, docs])
        self.assertEqual(out["skipped"], [])
