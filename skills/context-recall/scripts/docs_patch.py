"""Makes the docs patch of a calibration: the user's edits of doc files, as one unified diff that prep.sh applies to every
case's snapshot (DOCS_PATCH), so the runs with and without it differ in nothing else.

  docs_patch.py make --repo <path> --out <file> [--from <ref> --to <ref>] [--include-untracked]
By default the diff is the working tree (staged or not) against HEAD — nothing has to be committed; --from/--to take two
refs instead. Only doc files count (DOCS_GLOBS, comma-separated git pathspecs, default `*.md`); a code edit is left out.
Prints the files the patch touches. Exit 2 when there is no doc edit."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


# the user's git config never shapes the patch: prep.sh applies it with the a/ b/ prefixes, plain text, unquoted names
PLAIN = ["-c", "color.ui=false", "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "-c", "core.quotePath=false"]
DIFF = ["--no-color", "--no-ext-diff", "--no-textconv", "--src-prefix=a/", "--dst-prefix=b/"]


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *PLAIN, *a], capture_output=True, text=True, errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["make"])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="ref_from")
    ap.add_argument("--to", dest="ref_to")
    ap.add_argument("--include-untracked", action="store_true")
    a = ap.parse_args()
    specs = [g for g in os.environ.get("DOCS_GLOBS", "*.md").split(",") if g]
    if bool(a.ref_from) != bool(a.ref_to):
        sys.exit("docs_patch: give both --from and --to, or neither (the working tree)")
    refs = [a.ref_from, a.ref_to] if a.ref_from else ["HEAD"]
    diff = git(a.repo, "diff", *DIFF, *refs, "--", *specs).stdout
    files = set(git(a.repo, "diff", "--name-only", "-z", *refs, "--", *specs).stdout.split("\0"))   # deletions too
    if a.include_untracked and not a.ref_from:
        for f in git(a.repo, "ls-files", "-z", "--others", "--exclude-standard", "--", *specs).stdout.split("\0"):
            if f:
                diff += git(a.repo, "diff", *DIFF, "--no-index", "--", "/dev/null", f).stdout
                files.add(f)
    files = sorted(f for f in files if f)
    if not files:
        print("docs_patch: no doc edits found", file=sys.stderr); sys.exit(2)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(diff)
    print("\n".join(files))


if __name__ == "__main__":
    main()
