import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import STAND, run

FEATURE = {"id": "f01", "title": "Extend a booking", "request": "Let members extend their bookings.",
           "spec": {"text": "# Spec\nMembers extend a booking up to the next one."},
           "architecture": {"text": "# Plan\nReservationService.extend; a handler."},
           "tasks": [{"id": "T1", "title": "Service", "description": "Add extend to the service.", "commits": ["a" * 40],
                      "files": ["src/reservations/service.js"]},
                     {"id": "T2", "title": "Handler", "description": "Add the handler.", "commits": ["b" * 40],
                      "files": ["src/api/handlers.js"]}],
           "commits": ["a" * 40, "b" * 40]}


class Staged(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        (self.t / "features" / "f01").mkdir(parents=True)
        (self.t / "features" / "f01" / "feature.json").write_text(json.dumps(FEATURE))

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_one_record_per_stage(self):
        p = run(["python3", STAND / "history" / "staged.py", "--dir", self.t / "features", "--json"])
        self.assertEqual(p.returncode, 0, p.stderr)
        recs = {r["id"]: r for r in json.loads(p.stdout)["records"]}
        self.assertEqual(sorted(recs), ["f01:T1", "f01:T2", "f01:architecture", "f01:spec"])
        self.assertEqual({r["stage"] for r in recs.values()}, {"spec", "architecture", "task"})
        self.assertEqual({r["group"] for r in recs.values()}, {"f01"})
        self.assertEqual(recs["f01:spec"]["inputs"], [])
        self.assertEqual([i["label"] for i in recs["f01:architecture"]["inputs"]], ["Spec"])
        self.assertEqual([i["label"] for i in recs["f01:T1"]["inputs"]], ["Spec", "Architecture", "Task"])
        self.assertIn("Add extend to the service.", recs["f01:T1"]["inputs"][2]["original"])
        self.assertEqual(recs["f01:T1"]["commits"], ["a" * 40])
        self.assertEqual(recs["f01:spec"]["commits"], ["a" * 40, "b" * 40])

    def test_no_architecture_no_record(self):
        f = dict(FEATURE, architecture=None)
        (self.t / "features" / "f01" / "feature.json").write_text(json.dumps(f))
        recs = json.loads(run(["python3", STAND / "history" / "staged.py", "--dir", self.t / "features", "--json"]).stdout)["records"]
        self.assertNotIn("f01:architecture", [r["id"] for r in recs])
        self.assertEqual([i["label"] for i in recs[-1]["inputs"]], ["Spec", "Task"])
