import unittest

from tests.helpers import stand_module

score = stand_module("score")


class Cited(unittest.TestCase):
    def test_rule_without_a_source_is_not_cited(self):
        self.assertFalse(score.rule_cited([{"doc": "", "quote": "A cancelled booking cannot be extended"}], "any brief"))

    def test_rule_cited_by_its_doc(self):
        self.assertTrue(score.rule_cited([{"doc": "docs/a.md", "quote": "q"}], "see `docs/a.md:3`"))


class ToolLog(unittest.TestCase):
    def test_tool_log_skips_string_message(self):
        events = [{"type": "system", "subtype": "permission_denied", "message": "Permission to use Bash was denied."},
                  {"message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "a.md"}}]}},
                  {"message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "text"}]}}]
        self.assertEqual(score.tool_log(events), [("Read", {"file_path": "a.md"}, "text")])


class Outside(unittest.TestCase):
    """The runs root (BENCH) may sit anywhere, e.g. under macOS's /var/folders (a symlink to /private/var): a session reading
    its own clone or writing its own brief there is not outside."""

    def test_own_runs_root_is_not_outside(self):
        import os
        import tempfile
        from pathlib import Path
        from tests.helpers import stand_module as load
        runs = Path(tempfile.mkdtemp()) / "runs"
        os.environ["BENCH"] = str(runs)
        try:
            sc = load("score")
        finally:
            os.environ.pop("BENCH")
        calls = [("Read", {"file_path": f"{runs}/d01/BARE/docs/api.md"}, ""),
                 ("Read", {"file_path": f"{runs.resolve()}/d01/BARE/docs/api.md"}, ""),
                 ("Write", {"file_path": f"{runs}/d01/out/BARE-1/brief.md"}, ""),
                 # a TMPDIR ending in "/" gives the prompt's paths a double slash
                 ("Write", {"file_path": f"{runs.parent}//runs/d01/out/BARE-1/brief.md"}, "")]
        self.assertEqual(sc.outside_paths(calls, Path("/nowhere/session")), set())
        self.assertEqual(sc.outside_paths([("Read", {"file_path": "/var/lib/other/secret.md"}, "")],
                                          Path("/nowhere/session")), {"/var/lib/other/secret.md"})
