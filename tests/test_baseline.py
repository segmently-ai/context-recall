import tempfile
import unittest
from pathlib import Path

from tests.helpers import demo_repo, run


class Baseline(unittest.TestCase):
    def test_demo_repo_tags(self):
        with tempfile.TemporaryDirectory() as t:
            r = demo_repo(Path(t))
            tags = run(["git", "tag"], cwd=r).stdout.split()
            self.assertEqual(sorted(tags), ["d01", "d01-before", "d02", "d02-before", "d03", "d03-before"])

    def test_stand_in_version(self):
        self.assertEqual(run(["claude", "--version"]).stdout.strip(), "0.0.0 (stand-in)")
