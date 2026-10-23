"""Lists candidate tasks from merged pull requests (GitHub CLI `gh`): the description is the task's text, the merge commit
the candidate implementation. A pull request without a description is skipped: a title alone is not a task history.

Usage: pulls.py --repo <path> [--limit N] [--json]"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from records import Record, to_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not shutil.which("gh"):
        print("pulls: gh not found (GitHub CLI); install it and log in, or use another task history", file=sys.stderr)
        sys.exit(2)
    p = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", str(a.limit), "--json",
                        "number,title,body,mergeCommit,mergedAt,baseRefName"], cwd=a.repo, capture_output=True, text=True)
    if p.returncode:
        print(f"pulls: gh failed: {p.stderr.strip()[:300]}", file=sys.stderr)
        sys.exit(2)
    records, skipped = [], []
    for pr in sorted(json.loads(p.stdout), key=lambda x: x.get("mergedAt") or ""):
        rid = f"pr-{pr['number']}"
        body = (pr.get("body") or "").strip()
        if not body:
            skipped.append({"id": rid, "reason": "no description"}); continue
        sha = (pr.get("mergeCommit") or {}).get("oid")
        records.append(Record(id=rid, source="pulls", title=pr["title"][:80], request=f"{pr['title']}\n\n{body}",
                              commits=[sha] if sha else [], created=(pr.get("mergedAt") or "")[:10],
                              notes=f"merged into {pr.get('baseRefName', '')}"))
    if a.json:
        print(to_json(records, skipped))
    else:
        for r in records:
            print(f"{r.id:10} {r.created} {r.title}")
        for s in skipped:
            print(f"skipped {s['id']}: {s['reason']}")


if __name__ == "__main__":
    main()
