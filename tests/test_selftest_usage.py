import unittest

from tests.helpers import STAND, run


class SelftestUsage(unittest.TestCase):
    def test_usage_prints_the_whole_header(self):   # the --real cost line and the exit codes reach the user
        p = run([STAND / "selftest" / "selftest.sh", "--no-such-option"])
        self.assertEqual(p.returncode, 2)
        self.assertIn("28 sessions + 28 judge calls", p.stdout)
        self.assertIn("Exit 0 = every check passed.", p.stdout)
        self.assertNotIn("set -u", p.stdout)
