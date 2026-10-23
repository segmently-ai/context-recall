"""Maps a spec-kit history (`specs/<NNN-slug>/spec.md`, `plan.md`, `tasks.md`) to the staged format (history/STAGED.md):
one feature.json per feature folder. The request is the spec's `**Input**: User description: "…"` line (else its title);
the spec and the plan are the stage inputs; each top-level task line (`- [ ] T001 …` or `- [ ] **T001:** …`, sub-items
folded into their task) is a task, its files the paths its lines name, its commits the oldest commits after the feature's
spec that change those files (candidates for the tracer, never truth).

Usage: speckit.py --repo <path> --out <features dir> [--specs specs] [--max-commits N]"""
import argparse
import json
import re
import subprocess
from pathlib import Path

TASK = re.compile(r"^(\s*)-\s*\[[ xX]\]\s*\**(T\d+)(\.\d+)?\**:?\**\s*(.*)$")
PATH = re.compile(r"(?<![\w/])((?:[\w.@-]+/)+[\w.@-]+\.\w+)")
INPUT = re.compile(r'\*\*Input\*\*:\s*(?:User description:\s*)?"?(.+?)"?\s*$', re.M)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout.split()


def tasks_of(text):
    tasks = []
    for line in text.splitlines():
        m = TASK.match(line)
        if not m:
            continue
        tid, sub, body = m.group(2), m.group(3), m.group(4).strip()
        if sub and tasks and tasks[-1]["id"] == tid:
            tasks[-1]["description"] += f"\n- {body}"
        else:
            tasks.append({"id": tid, "title": re.sub(r"^\[[^\]]*\]\s*", "", body)[:120], "description": body})
    for t in tasks:
        t["files"] = list(dict.fromkeys(PATH.findall(t["description"])))
    return tasks


def feature(repo, folder, max_commits):
    spec = (folder / "spec.md").read_text(errors="replace")
    rel = folder.relative_to(repo).as_posix()
    first = (git(repo, "log", "--reverse", "--format=%H", "--", rel) or [""])[0]
    m = INPUT.search(spec)
    title = next((l.lstrip("# ").strip() for l in spec.splitlines() if l.startswith("#")), folder.name)
    tasks = tasks_of((folder / "tasks.md").read_text(errors="replace")) if (folder / "tasks.md").exists() else []
    rng = [f"{first}..HEAD"] if first else []
    for t in tasks:
        # the oldest after the spec (`-n` with `--reverse` would keep the newest)
        t["commits"] = git(repo, "log", "--reverse", "--format=%H", *rng, "--", *t["files"])[:max_commits] if t["files"] else []
    files = [f for t in tasks for f in t["files"]]
    # the paths the tasks name; when they name none, the oldest commits after the spec outside the specs folder
    where = files or [".", f":(exclude){Path(rel).parent.as_posix()}"]
    commits = git(repo, "log", "--reverse", "--format=%H", *rng, "--", *where)[:max_commits * 4] if rng else []
    plan = folder / "plan.md"
    return {"id": folder.name, "title": title.split(":", 1)[-1].strip(), "request": m.group(1).strip() if m else title,
            "spec": {"text": spec}, "architecture": {"text": plan.read_text(errors="replace")} if plan.exists() else None,
            "tasks": tasks, "commits": commits, "created": "", "source": f"{rel}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--specs", default="specs")
    ap.add_argument("--max-commits", type=int, default=10)
    a = ap.parse_args()
    repo, out = Path(a.repo).resolve(), Path(a.out)
    n = 0
    for folder in sorted((repo / a.specs).glob("*/")):
        if not (folder / "spec.md").exists():
            continue
        f = feature(repo, folder, a.max_commits)
        (out / folder.name).mkdir(parents=True, exist_ok=True)
        (out / folder.name / "feature.json").write_text(json.dumps(f, indent=1, ensure_ascii=False))
        n += 1
        print(f"{folder.name}: {len(f['tasks'])} tasks, {len(f['commits'])} candidate commits")
    print(f"{n} features → {out} (list them: staged.py --dir {out})")


if __name__ == "__main__":
    main()
