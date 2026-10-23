import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run

PRS = [{"number": 7, "title": "Extend a booking", "body": "Members want to extend their booking.\n\nCloses #3",
        "mergeCommit": {"oid": "a" * 40}, "mergedAt": "2026-01-02T12:00:00Z", "baseRefName": "main"},
       {"number": 8, "title": "Bump deps", "body": "", "mergeCommit": {"oid": "b" * 40},
        "mergedAt": "2026-01-03T12:00:00Z", "baseRefName": "main"}]


class Pulls(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.bin = self.t / "bin"; self.bin.mkdir()
        (self.t / "prs.json").write_text(json.dumps(PRS))
        (self.bin / "gh").write_text(f'#!/bin/sh\necho "$@" > {self.t}/gh-args\ncat {self.t}/prs.json\n')
        (self.bin / "gh").chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.t)

    def pulls(self, path):
        return run(["python3", STAND / "history" / "pulls.py", "--repo", self.t, "--json"], env={"PATH": path})

    def test_pr_records(self):
        p = self.pulls(f"{self.bin}:/usr/bin:/bin")
        self.assertEqual(p.returncode, 0, p.stderr)
        r = json.loads(p.stdout)["records"]
        self.assertEqual([x["id"] for x in r], ["pr-7"])
        self.assertEqual(r[0]["commits"], ["a" * 40])
        self.assertEqual(r[0]["created"], "2026-01-02")
        self.assertIn("Members want to extend their booking.", r[0]["request"])
        self.assertIn("--state merged", (self.t / "gh-args").read_text())

    def test_no_body_skipped(self):
        out = json.loads(self.pulls(f"{self.bin}:/usr/bin:/bin").stdout)
        self.assertEqual(out["skipped"], [{"id": "pr-8", "reason": "no description"}])

    def test_no_gh(self):
        p = self.pulls("/usr/bin:/bin")
        self.assertEqual(p.returncode, 2)
        self.assertIn("gh not found", p.stderr)
