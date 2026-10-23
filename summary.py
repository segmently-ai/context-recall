"""Summary of one case's cycle (cycle.sh): per session and per arm — cost, time, the tool used, files named, docs cited, rules
sighted in the session and rules stated in the brief (the judge's verdicts), the judge's extras and unsupported claims, the
audit. Inputs come from the scratch run dir while it exists, else from RESULTS/<tid>/ (after the clones are deleted), so the
table can always be rebuilt. Usage: summary.py <tid>"""
import json
import re
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402

B = stand.B
tid = sys.argv[1]
truth = json.loads((stand.TASKS / f"{tid}.truth.json").read_text())
R = stand.RESULTS / tid
RANK = {"provided": 3, "partial": 2, "wrong": 1, "absent": 0}
SHORT = {"provided": "p", "partial": "pa", "absent": "a", "wrong": "w"}
N = len(truth["rules"])


def run_file(ar, name):
    """A session's file: the scratch run dir, else the collected copy in RESULTS/<tid>/briefs/."""
    p = B / tid / "out" / ar / name
    return p if p.exists() else R / "briefs" / f"{ar}.{name}"


def sources(rule):
    return rule.get("sources") or ([{"doc": rule["doc"], "line": rule["line"]}] if rule.get("doc") else [])


def verdicts(v):
    """{rule id: verdict}; a rule written before the families (legacy_ids) takes its best member verdict."""
    raw = {x["id"]: x["verdict"] for x in v.get("must_know", [])}
    out = {}
    for rule in truth["rules"]:
        vs = [raw[x] for x in [rule["id"]] + rule.get("legacy_ids", []) if x in raw]
        out[rule["id"]] = max(vs, key=lambda q: RANK.get(q, -1)) if vs else None
    return out


names = set()
if (B / tid / "out").is_dir():
    names |= {d.name for d in (B / tid / "out").iterdir() if (d / "score.json").exists()}
if (R / "briefs").is_dir():
    names |= {p.name[:-len(".score.json")] for p in (R / "briefs").glob("*.score.json")}
AK = "areas" if "areas_modify" in truth else "modules"   # the case's areas, under its own key (optional)
MOD, REF = truth.get(f"{AK}_modify", []), truth.get(f"{AK}_reference", [])
areas = MOD + REF
rows = []
for ar in sorted(names, key=lambda x: (x.rsplit("-", 1)[0], int(x.rsplit("-", 1)[1]) if x.rsplit("-", 1)[1].isdigit() else 0)):
    s = json.loads(run_file(ar, "score.json").read_text())
    v_p = run_file(ar, "verdict.json"); v = json.loads(v_p.read_text()) if v_p.exists() else {}
    b_p = run_file(ar, "brief.md"); brief = b_p.read_text() if b_p.exists() else ""
    named = {a for a in areas if re.search(r"(?<![\w/-])" + re.escape(a.split("/")[-1]) + r"(?![\w-])", brief)}
    ex = v.get("extra_rules", [])
    rows.append({"ar": ar, "arm": ar.rsplit("-", 1)[0], "cost": s.get("cost_usd") or 0, "time": s.get("duration_s") or 0,
                 "used": s.get("tool_used"), "code": s["files"]["code_recall_any"], "prec": s["files"]["precision_raw"],
                 "areas": f"{len(named & set(MOD))}/{len(MOD)} / {len(named & set(REF))}/{len(REF)}",
                 "docs": f"{sum(d in brief for d in truth['docs_must_read'])}/{len(truth['docs_must_read'])}",
                 "sighted": sum(1 for x in s["rules"] if x["sighted"]),
                 "judge": verdicts(v), "error": "error" in v or not v_p.exists(),
                 "extras": f"{sum(x.get('verdict') == 'applies' for x in ex)}/{sum(x.get('verdict') == 'noise' for x in ex)}",
                 "unsupported": len(v.get("unsupported", [])), "audit": s.get("audit_flags") or []})

print(f"# Case {tid} — {truth['case']} (snapshot `{truth['snapshot']}`)\n")
if truth.get("stage"):
    print(f"Stage: {truth['stage']}" + (f" · feature {truth['group']}" if truth.get("group") else "")
          + (f" · inputs: {', '.join(i['label'] for i in truth.get('inputs', []))}" if truth.get("inputs") else "")
          + (f" · given by the input, not graded: {len(truth['given_rules'])} rules" if truth.get("given_rules") else "") + "\n")
print(f"Must-know rules: {N} items, {sum(len(sources(r)) for r in truth['rules'])} sources")
for r in truth["rules"]:
    print(f"- {r['id']}: " + (", ".join(f"{x['doc']}:{x['line']}" for x in sources(r)) or f"not written at the snapshot — {r['rule']}"))
A = bool(areas)
print("\n| Session | Cost | Time | Tool used | Code files | Precision | " + ("Areas modify / ref | " if A else "")
      + "Must-read docs cited | Rules sighted | Judge: provided / partial / absent / wrong | Extras applies/noise | Unsupported |")
print("|---|---|---|---|---|---|" + ("---|" if A else "") + "---|---|---|---|---|")
for r in rows:
    j = r["judge"]; cnt = lambda k: sum(1 for x in j.values() if x == k)
    print(f"| {r['ar']} | ${r['cost']:.2f} | {r['time']} s | {r['used']} | {r['code']} | {r['prec']} | "
          + (f"{r['areas']} | " if A else "") + f"{r['docs']} | {r['sighted']}/{N} | "
          + ("judge error | — | — |" if r["error"] else
             f"{cnt('provided')} / {cnt('partial')} / {cnt('absent')} / {cnt('wrong')} | {r['extras']} | {r['unsupported']} |"))
print("\n## Per arm (mean over sessions; a judge error is left out of the rule means)\n")
print("| Arm | Sessions | Cost | Time | Tool used | Rules sighted | Provided | Provided or partial |")
print("|---|---|---|---|---|---|---|---|")
for arm in dict.fromkeys(r["arm"] for r in rows):
    rs = [r for r in rows if r["arm"] == arm]; n = len(rs); rj = [r for r in rs if not r["error"]]
    m = lambda f: sum(f(r) for r in rj) / len(rj) if rj else float("nan")
    prov = m(lambda r: sum(x == "provided" for x in r["judge"].values()))
    pp = m(lambda r: sum(x in ("provided", "partial") for x in r["judge"].values()))
    j = lambda x: f"{x:.1f}/{N}" if rj else "judge errors only"
    print(f"| {arm} | {n} | ${sum(r['cost'] for r in rs) / n:.2f} | {sum(r['time'] for r in rs) / n:.0f} s | "
          f"{sum(1 for r in rs if r['used'])}/{n} | {sum(r['sighted'] for r in rs) / n:.1f}/{N} | {j(prov)} | {j(pp)} |")
print("\n## Rule by rule (judge verdict: p provided, pa partial, a absent, w wrong; ? no verdict)\n")
print("| Rule | " + " | ".join(r["ar"] for r in rows) + " |")
print("|---|" + "---|" * len(rows))
for rule in truth["rules"]:
    print(f"| {rule['id']} | " + " | ".join(SHORT.get(r["judge"].get(rule["id"]), "?") for r in rows) + " |")
flags = [f"{r['ar']}: {r['audit']}" for r in rows if r["audit"]]
print("\nAudit:", "; ".join(flags) if flags else "clean")
print(f"\nTotal cost: sessions ${sum(r['cost'] for r in rows):.2f}")
