"""The self-test's checks over a finished run, and its report. Usage: check.py <workspace> <runs dir> <real 0|1> <case>…  (RUN_LABEL: the run's label)

Every mode: each case has a summary without a traceback and a stand.json; every session of every arm has its brief, score
and verdict; no verdict is a judge error; the leak and path audit is clean; the clones are gone (--clean).
Stand-in mode also: every session used its arm's tool, saw every must-know rule in a tool result, and the stand-in judge
graded every rule provided (the stand-in brief cites every rule line). Real mode reports those numbers instead: they
measure the tools, not the harness; it checks that every session really ran (a cost above zero, no stand-in model), so an
earlier run's output can never pass for a real session. Exit 0 when every check passed."""
import json
import os
import sys
from pathlib import Path

K, runs_dir, real, cases = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] == "1", sys.argv[4:]
env = dict(l.split("=", 1) for l in (K / "stand.env").read_text().splitlines() if "=" in l and not l.startswith("#"))
arms = [a for a in env["ARMS"].split(",") if a]
runs = int(env.get("RUNS") or 1)
fails, rows = [], []
for c in cases:
    R = K / "results" / os.environ.get("RUN_LABEL", "") / c
    s = (R / "summary.md").read_text() if (R / "summary.md").exists() else ""
    if not s or "Traceback" in s:
        fails.append(f"{c}: no summary, or a traceback in it")
    if not (R / "stand.json").exists():
        fails.append(f"{c}: no stand.json")
    truth = json.loads((K / "tasks" / os.environ.get("RUN_LABEL", "") / f"{c}.truth.json").read_text())
    n = len(truth["rules"])
    if truth.get("stage") and f"Stage: {truth['stage']}" not in s:
        fails.append(f"{c}: the summary does not name its stage ({truth['stage']})")
    if any(g["source"] in {x["doc"] + ":" + str(x["line"]) for r in truth["rules"] for x in r.get("sources", [])}
           for g in truth.get("given_rules", [])):
        fails.append(f"{c}: a rule the input gives is also graded")
    left = [d.name for d in (runs_dir / c).iterdir() if (d / ".bench-base-ok").exists()] if (runs_dir / c).is_dir() else []
    if left:
        fails.append(f"{c}: clones left after --clean: {left}")
    for a in arms:
        for r in range(1, runs + 1):
            ar = f"{a}-{r}"; b = R / "briefs"
            missing = [x for x in ("brief.md", "score.json", "verdict.json") if not (b / f"{ar}.{x}").exists()]
            if missing:
                fails.append(f"{c} {ar}: missing {missing}"); continue
            sc, v = json.loads((b / f"{ar}.score.json").read_text()), json.loads((b / f"{ar}.verdict.json").read_text())
            if "error" in v:
                fails.append(f"{c} {ar}: judge error: {v['error'][:120]}"); continue
            prov = sum(x["verdict"] == "provided" for x in v.get("must_know", []))
            sighted = sum(x["sighted"] for x in sc["rules"])
            rows.append((c, ar, prov, sighted, n, sc["tool_used"], sc["files"]["code_recall_any"], sc.get("cost_usd") or 0))
            if sc["audit_flags"]:
                fails.append(f"{c} {ar}: audit flags {sc['audit_flags']}")
            if real and (not sc.get("cost_usd") or "stand-in" in (sc.get("model_usage") or {})):
                fails.append(f"{c} {ar}: not a real session (no cost, or the stand-in's model): an earlier run's output?")
            if not real:
                if sc["tool_used"] is not True:
                    fails.append(f"{c} {ar}: tool_used is {sc['tool_used']}")
                if sighted != n:
                    fails.append(f"{c} {ar}: {sighted}/{n} rules sighted (the stand-in reads every doc)")
                if prov != n:
                    fails.append(f"{c} {ar}: {prov}/{n} rules provided (the stand-in brief cites every rule)")
print("\n| Case | Session | Provided | Sighted | Tool used | Code files | Cost |\n|---|---|---|---|---|---|---|")
for c, ar, prov, sighted, n, used, code, cost in rows:
    print(f"| {c} | {ar} | {prov}/{n} | {sighted}/{n} | {used} | {code} | ${cost:.2f} |")
if real:
    unused = [f"{r[0]} {r[1]}" for r in rows if r[5] is not True]
    print("\nSessions that did not use their tool:", ", ".join(unused) or "none")
print()
for f in fails:
    print("FAIL", f)
print(f"self-test: {'PASS' if not fails else f'{len(fails)} failure(s)'} — {len(cases)} case(s), {len(rows)} session(s)"
      f"{' (real sessions)' if real else ' (stand-in claude)'}")
sys.exit(1 if fails else 0)
