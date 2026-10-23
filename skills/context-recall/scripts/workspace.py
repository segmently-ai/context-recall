"""The context-recall skill's workspace in a user's repository: `<repo>/.context-recall/` (git-ignored by its own
.gitignore) with stand.env, cases/, prereg/ and state.json (the phase reached, the run labels, the case lists).

  workspace.py init   --repo <path> [--arms A,B]   create it with the arms chosen (default: BARE, the agent alone); refuses
                                               a path with whitespace, or an existing workspace
  workspace.py arms   --repo <path> [--json]   the arms' cards: what each tool is, and the install it takes on this machine
  workspace.py arms   --repo <path> --set A,B  change the workspace's arms (BARE is always kept)
  workspace.py detect --repo <path> [--json]   the task histories found; exit 3 when there is none (the prerequisite)
  workspace.py status --repo <path>            the phase and the next step
  workspace.py phase  <name> --repo <path>     record a phase reached
The kit's scripts run with BENCH_WORKSPACE=<repo>/.context-recall."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]          # skills/context-recall/scripts/ → the kit root
PHASES = {   # phase → the next step, in order
    "selftest": "run the self-test (selftest/selftest.sh) to check the arms' tools on this machine",
    "configure": "set the arms and models in stand.env; add your own tool as an arm if you want one",
    "candidates": "list past tasks with the history adapter and pick 10–20 (a tuning and a held-out set)",
    "tracing": "trace each picked task into a case (subagents with CASE_AUTHORING.md), then validate_case.py",
    "prereg": "write the preregistration: question, stages, arms, cases, metrics, analysis",
    "pilot": "run one case, every arm, one session each, and read its summary",
    "batch": "run the remaining tuning cases, one at a time",
    "judge": "calibrate the judge on two tuning cases (calibrate.sh, compare_judges.py)",
    "numbers": "read stats.py --ref BARE (and --by stage) with the reading guide",
    "calibration": "edit the docs or tool settings, then compare two labelled runs (compare_runs.py); finally the held-out cases",
}


def ws_dir(repo):
    return Path(repo).resolve() / ".context-recall"


def template():
    for n in ("stand.env.example", "stand.env.template"):
        if (KIT / n).exists():
            return KIT / n
    sys.exit("context-recall: the kit has no stand.env template")


def arm_cards():
    """One card per arm adapter of the kit: family, about, status (ready | install | needs), missing, install. Status:
    `needs` = a command the install needs (uv, npm) is not on PATH; `install` = the tool itself is not installed yet."""
    pins = dict(re.findall(r"^([A-Z_]+)=(\S*)", template().read_text(), re.M))
    cards = []
    for p in sorted((KIT / "arms").glob("*.zsh"), key=lambda p: (p.stem != "BARE", p.stem)):
        f, text = p.stem, p.read_text()

        def field(k):
            m = re.search(rf"^ARM_{f}_{k}=(['\"])(.*)\1\s*$", text, re.M)
            return m.group(2) if m else ""
        install = re.sub(r"\$\{?([A-Z_]+)\}?", lambda m: pins.get(m.group(1)) or m.group(0), field("INSTALL"))
        missing = [n for n in field("NEEDS").split() if not shutil.which(n)]
        tool = field("BIN")
        status = "needs" if missing else "install" if (install and not tool) or (tool and not shutil.which(tool)) else "ready"
        cards.append({"family": f, "about": field("ABOUT") or field("TOOL"), "status": status, "missing": missing,
                      "install": install})
    return cards


def chosen_arms(spec):
    """BARE first, then the arms asked for, each once; exit 2 on an arm the kit has no adapter for."""
    known = {c["family"] for c in arm_cards()}
    asked = [a.strip() for a in (spec or "").split(",") if a.strip()]
    bad = [a for a in asked if a.split("-")[0] not in known]
    if bad:
        print(f"context-recall: no arm adapter for {', '.join(bad)} (arms: {', '.join(sorted(known))})", file=sys.stderr)
        sys.exit(2)
    return ",".join(dict.fromkeys(["BARE", *asked]))


def set_arms(env, arms):
    return re.sub(r"^ARMS=.*$", f"ARMS={arms}", env, flags=re.M)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace")


def detect(repo):
    """The task histories of a repository: [{"source", "count", "globs"? | "dir"?}]."""
    found = []
    files = git(repo, "grep", "-l", "-z", "-E", r"^##[[:space:]]+Run[[:space:]]*$", "--", "*.md").stdout.split("\0")
    files = [f for f in files if f]
    if files:   # one glob per folder that holds task files: never a glob over every doc of the repository
        dirs = sorted({str(Path(f).parent) for f in files})
        globs = ["*.md" if d == "." else f"{d}/*.md" for d in dirs]
        found.append({"source": "taskfiles", "count": len(files), "globs": globs})
    root = Path(repo)
    staged = [p.parent for p in root.glob("*/*/feature.json")]
    if staged:
        found.append({"source": "staged", "count": len(staged), "dir": str(staged[0].parent.relative_to(root))})
    speckit = [p.parent for p in root.glob("specs/*/spec.md") if (p.parent / "tasks.md").exists()]
    if speckit:
        found.append({"source": "speckit", "count": len(speckit), "dir": "specs"})
    if shutil.which("gh"):
        p = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", "20", "--json", "number,body"],
                           cwd=repo, capture_output=True, text=True)
        if p.returncode == 0:
            n = sum(1 for pr in json.loads(p.stdout or "[]") if (pr.get("body") or "").strip())
            if n:
                found.append({"source": "pulls", "count": n})
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["init", "arms", "detect", "status", "phase"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--arms", help="init: the arms to compare besides BARE, comma-separated")
    ap.add_argument("--set", help="arms: the workspace's new arms besides BARE, comma-separated")
    a = ap.parse_args()
    repo = Path(a.repo).resolve(); w = ws_dir(repo)
    if a.cmd == "arms" and a.set is not None:
        if not (w / "stand.env").exists():
            print(f"context-recall: no workspace at {w} (workspace.py init)", file=sys.stderr); sys.exit(2)
        arms = chosen_arms(a.set)
        (w / "stand.env").write_text(set_arms((w / "stand.env").read_text(), arms))
        print(f"arms: {arms}\nnext: bench.sh setup (installs or checks their tools)")
    elif a.cmd == "arms":
        cards = arm_cards()
        if a.json:
            print(json.dumps({"arms": cards}, indent=1))
        for c in [] if a.json else cards:
            print(f"{c['family']} — {c['about']}")
            if c["status"] == "ready":
                print("  ready: nothing to install")
            elif c["status"] == "install":
                print(f"  takes an install: {c['install']}")
            else:
                print(f"  needs {', '.join(c['missing'])} (not on this machine): install it, then {c['install']}")
    elif a.cmd == "init":
        arms = chosen_arms(a.arms)
        if re.search(r"\s", str(w)):
            print(f"context-recall: the kit cannot run on a path with whitespace: {w}", file=sys.stderr); sys.exit(2)
        if w.exists():
            print(f"context-recall: {w} exists (workspace.py status)", file=sys.stderr); sys.exit(2)
        if git(repo, "rev-parse", "--git-dir").returncode:
            print(f"context-recall: {repo} is not a git repository", file=sys.stderr); sys.exit(2)
        (w / "cases").mkdir(parents=True); (w / "prereg").mkdir()
        (w / ".gitignore").write_text("*\n")
        env = set_arms(re.sub(r"^HOST_REPO=.*$", f"HOST_REPO={repo}", template().read_text(), flags=re.M), arms)
        (w / "stand.env").write_text(env)
        (w / "state.json").write_text(json.dumps({"phase": "selftest", "labels": [], "tuning": [], "heldout": [],
                                                  "history": detect(repo)}, indent=1))
        print(f"workspace: {w}\narms: {arms}\nnext: {PHASES['selftest']}")
    elif a.cmd == "detect":
        found = detect(repo)
        if a.json:
            print(json.dumps({"sources": found}, indent=1))
        else:
            for f in found:
                where = " ".join(f.get("globs") or []) or f.get("dir")
                print(f"{f['source']}: {f['count']}" + (f" ({where})" if where else ""))
            if not found:
                print("no task history: the kit needs task texts in the repository (task files with a ## Run section, "
                      "a specs/ folder, or merged pull requests with a description) — commit subjects alone are not enough")
        sys.exit(0 if found else 3)
    else:
        if not (w / "state.json").exists():
            print(f"context-recall: no workspace at {w} (workspace.py init)", file=sys.stderr); sys.exit(2)
        state = json.loads((w / "state.json").read_text())
        if a.cmd == "phase":
            if a.name not in PHASES:
                print(f"context-recall: unknown phase {a.name} ({', '.join(PHASES)})", file=sys.stderr); sys.exit(2)
            state["phase"] = a.name
            (w / "state.json").write_text(json.dumps(state, indent=1))
        print(f"phase: {state['phase']}\nnext: {PHASES[state['phase']]}\nlabels: {', '.join(state['labels']) or 'none'}")
        # what the disk shows, so a recorded phase is never trusted alone
        cases = sorted((w / "cases").glob("*.case.json"))
        prereg = sorted(p.name for p in (w / "prereg").glob("*.md"))
        res = w / "results"
        runs = [(d.name, sum(1 for c in d.iterdir() if (c / "summary.md").exists()))
                for d in sorted(res.iterdir()) if d.is_dir()] if res.is_dir() else []
        print(f"cases: {len(cases)} · tuning {', '.join(state['tuning']) or '-'} · held-out {', '.join(state['heldout']) or '-'}")
        print(f"prereg: {', '.join(prereg) or 'none'}")
        print("results: " + (", ".join(f"{n} ({k} case{'s' if k != 1 else ''})" for n, k in runs if k) or "none"))


if __name__ == "__main__":
    main()
