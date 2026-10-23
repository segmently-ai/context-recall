"""Checks a case file (cases/<id>.case.json) against the host repository (HOST_REPO) before it is run.

Errors (exit 1): a missing key, an unknown verdict, an empty request (REQUEST_FIELD) on a case that is not rejected, a
snapshot or implementation commit not in the repository, a must-know rule without a doc:line source, a source doc missing at
the snapshot or a line past its end, a drop that names no reason, a strip entry outside the snapshot. Warnings: the
snapshot is not the parent of an implementation commit, a cited line is blank, a family with one member, a dropped rule
that uses a prescriptive word (never / must / do not / only / always: check it only describes behaviour), an edited or
must-read file missing at the snapshot, a request that names a file of the change or a rule's doc (a hint), a file of the
snapshot that holds the request or an input's original verbatim (a line of 40+ characters) and that neither the case's
strip list nor BASE_STRIP removes, a strip that removes a doc the case needs.
Usage: validate_case.py <case.json> [...]"""
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402

STAGES = ("brief", "spec", "architecture", "task")
KEYS = ["id", "verdict", "verdict_reason", "snapshot", "implementation_commits", "truth", "must_know_rules",
        "undocumented_rules", "correct_approach", "wrong_approaches", "grading"]
TRUTH_KEYS = ["files_edit", "files_read", "docs_must_read"]
REF = re.compile(r"([\w./@-]+\.md):(\d+)(?:[-–](\d+))?")
PRESCRIBES = re.compile(r"(?i)\b(never|must|do not|don't|only|always)\b")


def git(*args):
    r = subprocess.run(["git", "-C", str(stand.HOST), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def check(path):
    err, warn = [], []
    c = json.loads(Path(path).read_text())
    err += [f"missing key: {k}" for k in KEYS if k not in c]
    err += [f"missing key: truth.{k}" for k in TRUTH_KEYS if k not in c.get("truth", {})]
    if c.get("verdict") not in ("good", "weak", "reject"):
        err.append(f"verdict must be good, weak or reject: {c.get('verdict')!r}")
    stage = c.get("stage", "brief")
    if stage not in STAGES:
        err.append(f"stage must be one of {', '.join(STAGES)}: {stage!r}")
    elif stage in ("architecture", "task") and not any((i.get("text") or "").strip() for i in c.get("inputs") or []):
        err.append(f"a {stage} case needs inputs: what the stage received (label, original, text)")
    if err or c.get("verdict") == "reject":   # a rejected case is kept for the record, never run
        return err, warn
    field = stand.cfg("REQUEST_FIELD", "request_en")
    if not (c.get(field) or "").strip():
        return err + [f"empty request: {field} (REQUEST_FIELD)"], warn
    strips = c.get("strip") or []
    err += [f"strip entry outside the snapshot: {g!r}" for g in strips
            if not isinstance(g, str) or not g.strip() or g.startswith("/") or ".." in g]
    snap = c["snapshot"]
    if git("cat-file", "-e", f"{snap}^{{commit}}")[0]:
        return err + [f"snapshot {snap} is not a commit of {stand.HOST}"], warn
    parents = set()
    for ic in c["implementation_commits"]:
        rc, out = git("rev-list", "--parents", "-n", "1", ic["sha"])
        if rc:
            err.append(f"implementation commit {ic['sha']} is not in the repository"); continue
        parents |= set(out.split()[1:])
    full = git("rev-parse", snap)[1].strip()
    if c["implementation_commits"] and full not in parents:
        warn.append("the snapshot is the parent of no implementation commit (it should be the parent of the first)")
    docs = {}

    def lines(doc):
        if doc not in docs:
            rc, out = git("show", f"{snap}:{doc}")
            docs[doc] = None if rc else out.split("\n")
        return docs[doc]
    def sources_ok(name, r):   # every doc:line of a rule's source exists at the snapshot
        refs = [(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in REF.finditer(r.get("source", ""))]
        if not refs:
            err.append(f"{name}: no doc:line in its source ({r.get('source')!r})"); return
        for doc, a, b in refs:
            ls = lines(doc)
            if ls is None:
                err.append(f"{name}: {doc} is not in the snapshot"); continue
            if b > len(ls) or a < 1:
                err.append(f"{name}: {doc}:{a} is past the doc's end ({len(ls)} lines)"); continue
            if not any(x.strip() for x in ls[a - 1:b]):
                warn.append(f"{name}: {doc}:{a} is a blank line")
    for i, r in enumerate(c.get("given_rules") or [], 1):
        sources_ok(f"given rule {i}", r)
    fams = {}
    for i, r in enumerate(c["must_know_rules"], 1):
        sources_ok(f"rule {i}", r)
        if r.get("family"):
            fams.setdefault(r["family"], []).append(i)
        if "drop" in r:
            if not str(r["drop"]).strip():
                err.append(f"rule {i}: a drop names no reason")
            if PRESCRIBES.search(r.get("rule", "")):   # a word can describe behaviour too ("logged per request only"): judge it
                warn.append(f"rule {i}: a dropped rule says {PRESCRIBES.search(r['rule']).group(0)!r} — check it only "
                            "describes behaviour and no wrong approach breaks it")
    warn += [f"family {f}: one member (rule {m[0]})" for f, m in fams.items() if len(m) < 2]
    for f in c["truth"]["files_edit"]:
        if git("cat-file", "-e", f"{snap}:{f['path']}")[0]:
            warn.append(f"edited file not at the snapshot (created by the change?): {f['path']}")
    for d in c["truth"]["docs_must_read"]:
        if lines(d["doc"]) is None:
            warn.append(f"must-read doc not at the snapshot: {d['doc']}")
    for sp in (c.get("seed") or {}).get("paths", []):   # the operator's seed must point at something the agent can open
        if git("cat-file", "-e", f"{snap}:{sp.rstrip('/')}")[0]:
            warn.append(f"seed path not at the snapshot: {sp}")
    req = c[field]
    for f in c["truth"]["files_edit"]:
        if Path(f["path"]).name in req:
            warn.append(f"the request names a file of the change: {Path(f['path']).name}")
    rule_docs = {m.group(1) for r in c["must_know_rules"] for m in REF.finditer(r.get("source", ""))}
    for doc in rule_docs:
        if doc in req:
            warn.append(f"the request names a rule's doc: {doc}")
    for inp in c.get("inputs") or []:   # an input is reworked like the request: no file of the change, no rule's doc
        text = inp.get("text") or ""
        if not inp.get("original"):
            warn.append(f"input {inp.get('label')!r}: no original kept")
        warn += [f"an input names a file of the change: {Path(f['path']).name}" for f in c["truth"]["files_edit"]
                 if Path(f["path"]).name in text]
        warn += [f"an input names a rule's doc: {doc}" for doc in rule_docs if doc in text]
    # the task's own text left in the snapshot (its task file, the feature's spec) hands every arm the answer: strip it
    globs = [g for g in strips if isinstance(g, str)] + [g for g in stand.cfg("BASE_STRIP", "").split(",") if g]

    def stripped(p):   # p, or a folder above it, matches a glob of the case's strip list or BASE_STRIP
        parts = p.split("/")
        return any(fnmatch.fnmatchcase("/".join(parts[:k]), g) for g in globs for k in range(1, len(parts) + 1))

    def held(text):   # the snapshot's files holding a line of the text (40+ characters) verbatim, not stripped
        needles = sorted({x.strip() for x in text.split("\n") if len(x.strip()) >= 40})
        if not needles:
            return []
        out = git("grep", "-l", "-F", "-I", *[a for n in needles for a in ("-e", n)], snap, "--")[1]
        return sorted({x[len(snap) + 1:] for x in out.splitlines() if x.startswith(f"{snap}:")} - {""})
    warn += [f"the snapshot holds the request verbatim: {p} (add it to the case's strip list)"
             for p in held(req) if not stripped(p)]
    for inp in c.get("inputs") or []:
        warn += [f"the snapshot holds input {inp.get('label')!r} verbatim: {p} (add it to the case's strip list)"
                 for p in held(inp.get("original") or "") if not stripped(p)]
    needed = {d["doc"] for d in c["truth"]["docs_must_read"]} | rule_docs
    warn += [f"the strip list removes a doc the case needs: {d}" for d in sorted(needed) if stripped(d)]
    return err, warn


def main():
    bad = 0
    for p in sys.argv[1:]:
        err, warn = check(p)
        print(f"{p}: {'ok' if not err else 'ERRORS'}" + (f" ({len(warn)} warnings)" if warn else ""))
        for e in err:
            print("  error:", e)
        for w in warn:
            print("  warning:", w)
        bad += bool(err)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
