"""Lists candidate cases from a staged history (history/STAGED.md): one folder per feature with its feature.json. Each feature
gives one record per stage — `spec` (the request), `architecture` (the request; the spec as input) when the feature has
one, and one `task` record per task (the request; the spec, the architecture and the task as inputs) — so a case can be
traced for every stage of the same feature.

Usage: staged.py --dir <features dir> [--json]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from records import Record, to_json  # noqa: E402


def records_of(f):
    fid, req, out = f["id"], f["request"], []
    spec = [{"label": "Spec", "original": f["spec"]["text"]}]
    arch = [{"label": "Architecture", "original": f["architecture"]["text"]}] if f.get("architecture") else []
    common = dict(source="staged", group=fid, created=f.get("created", ""), notes=f.get("title", ""))
    out.append(Record(id=f"{fid}:spec", title=f.get("title", fid), request=req, commits=f.get("commits", []),
                      stage="spec", **common))
    if arch:
        out.append(Record(id=f"{fid}:architecture", title=f.get("title", fid), request=req, inputs=spec,
                          commits=f.get("commits", []), stage="architecture", **common))
    for t in f.get("tasks", []):
        task = [{"label": "Task", "original": f"{t.get('title', '')}\n\n{t.get('description', '')}".strip()}]
        out.append(Record(id=f"{fid}:{t['id']}", title=t.get("title", t["id"])[:80], request=req, inputs=spec + arch + task,
                          commits=t.get("commits", []), stage="task", **common))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    records, skipped = [], []
    for p in sorted(Path(a.dir).glob("*/feature.json")):
        try:
            records += records_of(json.loads(p.read_text()))
        except (KeyError, ValueError) as e:
            skipped.append({"path": str(p), "reason": f"not a staged feature: {e}"})
    if a.json:
        print(to_json(records, skipped))
    else:
        for r in records:
            print(f"{r.id:28} {r.stage:13} {len(r.commits):3} commits  {r.title}")
        for s in skipped:
            print(f"skipped {s['path']}: {s['reason']}")


if __name__ == "__main__":
    main()
