"""Lists candidate tasks from task files: Markdown files with a `## Run` section (the task, as the operator wrote it) and
an optional `## Read` section (the docs and files the operator named: the seed). Every git version of a file whose `## Run`
text changed is one candidate; its commits are the ones after that version, up to the next one, that change other files
(a range for the tracer to confirm, never truth). A file the globs match without a `## Run` heading (a plain doc) is not a
task file: not listed, and a commit that changes it is a candidate like any other. An untracked task file is skipped,
never guessed.

Usage: taskfiles.py --repo <path> --glob '<glob relative to the repo>' [--glob …] [--json] [--max-commits N]"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from records import Record, to_json  # noqa: E402


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def sections(text):
    """{lower-case heading: body} for every `## ` heading."""
    out, cur = {}, None
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1).strip().lower(); out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def seed_paths(read, root):
    """The paths of a `## Read` section, repo-relative; an absolute path outside the repository is dropped."""
    out = []
    for line in read.splitlines():
        s = line.strip().lstrip("-*").strip().strip("`").strip()
        if not s or " " in s:
            continue
        if s.startswith("/"):
            try:
                s = str(Path(s).relative_to(root))
            except ValueError:
                continue
        out.append(s)
    return out


RUN = re.compile(r"^##[ \t]+Run[ \t]*$", re.M)


def records_of(repo, rel, max_commits, tasks):
    """The candidates of one task file; tasks: every task file of the globs (a commit that writes only those is none)."""
    rc, log = git(repo, "log", "--reverse", "--format=%H%x09%cI", "--", rel)
    versions, last_run = [], None
    for line in log.splitlines():
        sha, date = line.split("\t")
        secs = sections(git(repo, "show", f"{sha}:{rel}")[1])
        run = secs.get("run", "")
        if run and run != last_run:
            versions.append((sha, date, run, secs.get("read", "")))
            last_run = run
    out = []
    for k, (sha, date, run, read) in enumerate(versions, 1):
        end = versions[k][0] if k < len(versions) else "HEAD"
        # a window of the oldest commits after this version (a large repository has thousands after a task's last
        # version), their changed files in ONE git call; commits that change only the task file itself are not candidates
        ids = git(repo, "rev-list", "--reverse", f"{sha}..{end}")[1].split()[:max_commits * 4]
        changed, cur = {}, None
        if ids:
            for line in git(repo, "log", "--no-walk=unsorted", "--name-only", "--format=@@%H", *ids)[1].splitlines():
                if line.startswith("@@"):
                    cur = line[2:]; changed[cur] = set()
                elif line.strip() and cur:
                    changed[cur].add(line.strip())
        # a commit that only writes task files (this one, or the next tasks') is no implementation
        commits = [c for c in ids if any(f not in tasks for f in changed.get(c, ()))][:max_commits]
        title = next((l.strip() for l in run.splitlines() if l.strip()), "")[:80]
        paths = seed_paths(read, repo)
        out.append(Record(id=f"{Path(rel).stem}-{k}", source="taskfiles", title=title, request=run,
                          seed={"text": "", "paths": paths} if paths else None, commits=commits,
                          created=date[:10], notes=f"{rel} @ {sha[:9]}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--glob", action="append", required=True, help="repeat it for task files in several folders")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-commits", type=int, default=50)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    records, skipped = [], []
    files = sorted({f.relative_to(repo).as_posix() for g in a.glob for f in repo.glob(g) if f.is_file()})
    tasks = [rel for rel in files if RUN.search((repo / rel).read_text(encoding="utf-8", errors="replace"))]
    for rel in tasks:
        if git(repo, "ls-files", "--error-unmatch", "--", rel)[0]:
            skipped.append({"path": rel, "reason": "untracked"}); continue
        found = records_of(repo, rel, a.max_commits, set(tasks))
        if not found:
            skipped.append({"path": rel, "reason": "no committed version with a ## Run section"})
        records += found
    if a.json:
        print(to_json(records, skipped))
    else:
        for r in records:
            print(f"{r.id:32} {r.created} {len(r.commits):3} commits  {r.title}")
        for s in skipped:
            print(f"skipped {s['path']}: {s['reason']}")


if __name__ == "__main__":
    main()
