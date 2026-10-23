"""The numbers over cases, per arm, from RESULTS/<id>/briefs/ (the collected sessions) and tasks/<id>.truth.json.

Per case and arm: the mean over sessions of the items provided, and provided or partial (a session with a judge error is left
out of the means, never counted absent), the items sighted in the session, code recall, cost, time and the tool-used flag.
Per arm, over cases: the sum of the per-case means over the sum of graded items (cases with more items weigh more), with a
95% interval from a case bootstrap: the cases are drawn with replacement, each with all its items and sessions, 10,000
times with a fixed seed. Against a reference arm (--ref): per case the arm's share minus the reference's share, the mean of
those differences over the cases both arms ran, its bootstrap interval, and the cases better / worse / equal.

Usage: stats.py [--ref ARM] [--arms A,B,…] [--draws N] [--json] [id …]   (no ids: every case with results)"""
import argparse
import json
import random
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402

RANK = {"provided": 3, "partial": 2, "wrong": 1, "absent": 0}


def frac(s):
    a, b = s.split("/")
    return int(a), int(b)


def case_rows(tid):
    """{arm: {n_items, prov, pp, sighted, code, cost, time, used, sessions, judged}} for one case (means over sessions)."""
    truth = json.loads((stand.TASKS / f"{tid}.truth.json").read_text())
    rules = truth["rules"]; n = len(rules)
    out = {}
    for sp in sorted((stand.RESULTS / tid / "briefs").glob("*.score.json")):
        ar = sp.name[:-len(".score.json")]; arm = ar.rsplit("-", 1)[0]
        s = json.loads(sp.read_text())
        vp = sp.with_name(f"{ar}.verdict.json")
        v = json.loads(vp.read_text()) if vp.exists() else {"error": "no verdict"}
        a = out.setdefault(arm, {"n_items": n, "prov": [], "pp": [], "sighted": [], "code": [], "cost": [], "time": [],
                                 "used": []})
        a["sighted"].append(sum(1 for x in s["rules"] if x["sighted"]))
        a["code"].append(frac(s["files"]["code_recall_any"]))
        a["cost"].append(s.get("cost_usd") or 0); a["time"].append(s.get("duration_s") or 0)
        a["used"].append(bool(s.get("tool_used")))
        if "error" in v:
            continue
        raw = {x["id"]: x["verdict"] for x in v.get("must_know", [])}
        fam = []
        for r in rules:
            vs = [raw[x] for x in [r["id"]] + r.get("legacy_ids", []) if x in raw]
            fam.append(max(vs, key=lambda q: RANK.get(q, -1)) if vs else "absent")
        a["prov"].append(sum(x == "provided" for x in fam)); a["pp"].append(sum(x in ("provided", "partial") for x in fam))
    rows = {}
    for arm, a in out.items():
        mean = lambda xs: sum(xs) / len(xs) if xs else None
        rows[arm] = {"n_items": a["n_items"], "prov": mean(a["prov"]), "pp": mean(a["pp"]), "sighted": mean(a["sighted"]),
                     "code_hit": sum(x for x, _ in a["code"]), "code_tot": sum(y for _, y in a["code"]),
                     "cost": a["cost"], "time": a["time"], "used": a["used"], "sessions": len(a["cost"]), "judged": len(a["prov"])}
    return rows


def pooled(rows, key, cases):
    cs = [c for c in cases if rows[c][key] is not None]
    den = sum(rows[c]["n_items"] for c in cs)
    return sum(rows[c][key] for c in cs) / den if den else float("nan")


def boot(f, cases, draws, seed=1):
    rng, xs = random.Random(seed), []
    for _ in range(draws):
        xs.append(f([rng.choice(cases) for _ in cases]))
    xs.sort()
    return xs[int(0.025 * draws)], xs[int(0.975 * draws)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--ref", help="the reference arm of the paired differences")
    ap.add_argument("--arms", help="only these arms, comma-separated")
    ap.add_argument("--draws", type=int, default=10000)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--by", choices=["stage", "group", "seeded"], help="one table per stage, feature, or seeded/unseeded")
    a = ap.parse_args()
    ids = a.ids or sorted(p.name for p in stand.RESULTS.iterdir() if (p / "briefs").is_dir() and (stand.TASKS / f"{p.name}.truth.json").exists())
    per = {tid: case_rows(tid) for tid in ids}
    if not a.by:
        return report(ids, per, a)
    blocks = {}
    for tid in ids:
        t = json.loads((stand.TASKS / f"{tid}.truth.json").read_text())
        key = {"stage": f"Stage {t.get('stage', 'brief')}", "group": f"Feature {t.get('group') or '-'}",
               "seeded": "Seeded" if t.get("seeded") else "Unseeded"}[a.by]
        blocks.setdefault(key, []).append(tid)
    for key in sorted(blocks):
        print(f"## {key}\n")
        report(blocks[key], {t: per[t] for t in blocks[key]}, a)
        print()


def report(ids, per, a):
    arms = sorted({arm for r in per.values() for arm in r})
    if a.arms:
        arms = [x for x in a.arms.split(",") if x in arms]
    res = {"cases": ids, "arms": {}}
    for arm in arms:
        rows = {c: per[c][arm] for c in ids if arm in per[c]}
        cs = [c for c in rows if rows[c]["prov"] is not None]
        if not cs:
            continue
        cost = [x for c in rows for x in rows[c]["cost"]]; time = [x for c in rows for x in rows[c]["time"]]
        used = [x for c in rows for x in rows[c]["used"]]
        prov_items = sum(rows[c]["prov"] * rows[c]["judged"] for c in cs)   # items provided over all judged sessions
        R = {"cases": len(cs), "sessions": len(cost), "items": sum(rows[c]["n_items"] for c in cs),
             "provided": pooled(rows, "prov", cs), "provided_ci": boot(lambda d: pooled(rows, "prov", d), cs, a.draws),
             "provided_or_partial": pooled(rows, "pp", cs), "pp_ci": boot(lambda d: pooled(rows, "pp", d), cs, a.draws),
             "sighted": pooled(rows, "sighted", cs),
             "code_recall": sum(rows[c]["code_hit"] for c in rows) / max(1, sum(rows[c]["code_tot"] for c in rows)),
             "cost_per_session": sum(cost) / len(cost), "time_per_session_s": sum(time) / len(time),
             "cost_per_provided_item": sum(x for c in cs for x in rows[c]["cost"]) / prov_items if prov_items else None,
             "tool_used": f"{sum(used)}/{len(used)}"}
        if a.ref and a.ref != arm:
            both = [c for c in cs if a.ref in per[c] and per[c][a.ref]["prov"] is not None]
            if both:
                d = {c: (rows[c]["prov"] - per[c][a.ref]["prov"]) / rows[c]["n_items"] for c in both}
                R["vs_ref"] = {"ref": a.ref, "cases": len(both), "mean_diff": sum(d.values()) / len(both),
                               "ci": boot(lambda cs_: sum(d[c] for c in cs_) / len(cs_), both, a.draws),
                               "better": sum(x > 0 for x in d.values()), "worse": sum(x < 0 for x in d.values()),
                               "equal": sum(x == 0 for x in d.values())}
        res["arms"][arm] = R
    if a.json:
        print(json.dumps(res, indent=1)); return
    pc = lambda x: f"{100 * x:.0f}%"
    ci = lambda t: f"{100 * t[0]:.0f}–{100 * t[1]:.0f}%"
    print(f"Cases: {' '.join(ids)} · intervals: 95%, case bootstrap, {a.draws} draws\n")
    print("| Arm | Cases | Sessions | Provided | 95% | Provided or partial | 95% | Sighted | Code recall | Cost/session | "
          "Time/session | Cost per provided item | Tool used |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arm, R in res["arms"].items():
        cpi = f"${R['cost_per_provided_item']:.2f}" if R["cost_per_provided_item"] else "—"
        print(f"| {arm} | {R['cases']} | {R['sessions']} | {pc(R['provided'])} | {ci(R['provided_ci'])} | "
              f"{pc(R['provided_or_partial'])} | {ci(R['pp_ci'])} | {pc(R['sighted'])} | {pc(R['code_recall'])} | "
              f"${R['cost_per_session']:.2f} | {R['time_per_session_s']:.0f} s | {cpi} | {R['tool_used']} |")
    if a.ref:
        print(f"\nPaired against {a.ref} (per case: the arm's share provided minus {a.ref}'s; mean over the cases both ran)\n")
        print("| Arm | Cases | Mean difference | 95% | Better / worse / equal |\n|---|---|---|---|---|")
        for arm, R in res["arms"].items():
            v = R.get("vs_ref")
            if v:
                print(f"| {arm} | {v['cases']} | {100 * v['mean_diff']:+.0f} pts | {100 * v['ci'][0]:+.0f} … {100 * v['ci'][1]:+.0f} | "
                      f"{v['better']} / {v['worse']} / {v['equal']} |")


if __name__ == "__main__":
    main()
