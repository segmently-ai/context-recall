import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, demo_repo, run, workspace

MAKE = STAND / "skills" / "context-recall" / "scripts" / "docs_patch.py"
ID = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
      "GIT_COMMITTER_EMAIL": "t@example.com"}
LINE = "- A cancelled booking cannot be extended."


class DocsPatch(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.repo = demo_repo(self.t)
        self.ws = workspace(self.t, self.repo)
        self.env = {"BENCH_WORKSPACE": str(self.ws), "BENCH": str(self.t / "runs"), "RUN_LABEL": "b"}

    def tearDown(self):
        shutil.rmtree(self.t)

    def make(self, *extra, env=None):
        out = self.t / "edit.patch"
        p = run(["python3", MAKE, "make", "--repo", self.repo, "--out", out, *extra], env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return out, p.stdout

    def prep(self, patch=None, cwd=None):
        env = dict(self.env, **({"DOCS_PATCH": str(patch)} if patch else {}))
        return run([STAND / "prep.sh", "d01", "d01-before", "BARE"], env=env, cwd=cwd)

    def test_make_takes_doc_edits_only(self):
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        (self.repo / "src" / "api" / "schema.js").write_text("// edited\n")
        (self.repo / "docs" / "new.md").write_text("# New\n")
        out, listing = self.make("--include-untracked")
        text = out.read_text()
        self.assertIn(LINE, text)
        self.assertIn("docs/new.md", text)
        self.assertNotIn("schema.js", text)
        self.assertIn("docs/reservations.md", listing)

    def test_patch_applied(self):
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        patch, _ = self.make()
        p = self.prep(patch)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(LINE, (self.t / "runs" / "b" / "d01" / "BARE" / "docs" / "reservations.md").read_text())

    def test_non_doc_refused(self):
        bad = self.t / "bad.patch"
        bad.write_text("--- a/src/a.js\n+++ b/src/a.js\n@@ -0,0 +1 @@\n+x\n")
        p = self.prep(bad)
        self.assertEqual(p.returncode, 2)
        self.assertIn("touches a non-doc file: src/a.js", p.stdout + p.stderr)

    def test_unapplied_excluded(self):
        (self.repo / "docs" / "equipment.md").write_text("# Equipment\n\nrewritten entirely\n")
        run(["git", "-C", self.repo, "commit", "-qam", "rewrite"], env=ID)
        with open(self.repo / "docs" / "equipment.md", "a") as f:
            f.write("more\n")
        patch, _ = self.make()   # its context is the rewritten doc, absent at d01-before
        p = self.prep(patch)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("did not apply", (self.ws / "results" / "b" / "d01" / "excluded.txt").read_text())

    def test_cycle_leaves_an_unapplied_case_out(self):
        (self.ws / "cases").mkdir()
        shutil.copy(STAND / "selftest" / "cases" / "d01-extend-booking.case.json", self.ws / "cases")
        (self.repo / "docs" / "equipment.md").write_text("# Equipment\n\nrewritten entirely\n")
        run(["git", "-C", self.repo, "commit", "-qam", "rewrite"], env=ID)
        with open(self.repo / "docs" / "equipment.md", "a") as f:
            f.write("more\n")
        patch, _ = self.make()
        p = run([STAND / "bench.sh", "case", "d01", "--clean"], env=dict(self.env, DOCS_PATCH=str(patch)))
        self.assertEqual(p.returncode, 0, p.stdout[-600:] + p.stderr[-600:])
        R = self.ws / "results" / "b" / "d01"
        self.assertTrue((R / "excluded.txt").exists())
        self.assertFalse((R / "summary.md").exists())
        self.assertIn('"docs_patch"', (R / "stand.json").read_text())

    def test_base_of_another_patch_refused(self):
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        patch, _ = self.make()
        self.assertEqual(self.prep(patch).returncode, 0)
        shutil.rmtree(self.t / "runs" / "b" / "d01" / "BARE")
        p = self.prep()
        self.assertEqual(p.returncode, 2)
        self.assertIn("another docs patch", p.stdout + p.stderr)

    def test_relative_patch_path(self):   # the path is the caller's, not the snapshot's
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        self.make()
        p = self.prep("edit.patch", cwd=self.t)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(LINE, (self.t / "runs" / "b" / "d01" / "BARE" / "docs" / "reservations.md").read_text())

    def test_not_a_patch_refused(self):   # never "excluded" case by case: the run as a whole is wrong
        bad = self.t / "bad.patch"
        bad.write_text("these are notes, not a diff\n")
        p = self.prep(bad)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("not a patch", p.stdout + p.stderr)
        self.assertFalse((self.ws / "results" / "b" / "d01" / "excluded.txt").exists())

    def test_make_ignores_user_git_config(self):
        cfg = self.t / "gitconfig"
        cfg.write_text("[diff]\n\tnoprefix = true\n\tmnemonicPrefix = true\n[color]\n\tui = always\n")
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        patch, listing = self.make(env={"GIT_CONFIG_GLOBAL": str(cfg)})
        text = patch.read_text()
        self.assertIn("+++ b/docs/reservations.md", text)
        self.assertNotIn("\x1b[", text)
        self.assertIn("docs/reservations.md", listing)
        self.assertEqual(self.prep(patch).returncode, 0)

    def test_resume_with_another_patch_refused(self):   # after --clean no base is left to tell: stand.json tells
        (self.ws / "cases").mkdir()
        shutil.copy(STAND / "selftest" / "cases" / "d01-extend-booking.case.json", self.ws / "cases")
        with open(self.repo / "docs" / "reservations.md", "a") as f:
            f.write(LINE + "\n")
        patch, _ = self.make()
        p = run([STAND / "bench.sh", "case", "d01", "--clean"], env=dict(self.env, DOCS_PATCH=str(patch)))
        self.assertEqual(p.returncode, 0, p.stdout[-600:] + p.stderr[-600:])
        p = run([STAND / "bench.sh", "case", "d01", "--clean", "--resume"], env=self.env)
        self.assertEqual(p.returncode, 2, p.stdout[-600:] + p.stderr[-600:])
        self.assertIn("docs patch", p.stderr)

    def test_make_counts_a_deleted_doc(self):
        (self.repo / "docs" / "equipment.md").unlink()
        _, listing = self.make()
        self.assertIn("docs/equipment.md", listing)
