"""Compares two labelled runs (RUN_LABEL) on the same cases — the calibration report: did an edit of the docs or of a
tool's settings change what each arm puts in front of the agent?

Per stage and arm: the share of rule items provided, and provided or partial, in run A and in run B (per case the mean over
its judged sessions), the paired difference over the cases both runs hold, its 95% interval from a case bootstrap (seed 1),
the cases better / worse / equal, and per case and arm the rules gained (provided in some session of B, in none of A) and
lost. A case is left out when one run lacks it or marked it excluded (`excluded.txt`, e.g. a docs patch that did not apply).
The two runs must use the same key and the same arms, each its cases one docs patch (their `stand.json`), and every case
the same truth (snapshot, strip list, rule ids and texts — the case file unchanged between the runs); otherwise there is
nothing to compare (exit 2).

Usage: compare_runs.py <label A> <label B> [id …] [--out <file>] [--draws N]"""
import argparse
import json
import random
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402

RANK = {"provided": 3, "partial": 2, "wrong": 1, "absent": 0}


def verdicts(truth, v):
    raw = {x["id"]: x["verdict"] for x in v.get("must_know", [])}
    out = {}
    for r in truth["rules"]:
        vs = [raw[x] for x in [r["id"]] + r.get("legacy_ids", []) if x in raw]
        out[r["id"]] = max(vs, key=lambda q: RANK.get(q, -1)) if vs else "absent"
    return out


def load(label, cid):
    """One case of one run: (data, None), or (None, why it is left out)."""
    R = stand.results_for(label) / cid
    if not (R / "briefs").is_dir():
        return None, "no results"
    if (R / "excluded.txt").exists():
        return None, (R / "excluded.txt").read_text().strip()
    tp = stand.tasks_for(label) / f"{cid}.truth.json"   # each run's own key; an older layout kept one tasks/ for all
    truth = json.loads((tp if tp.exists() else stand.tasks_for(None) / f"{cid}.truth.json").read_text())
    runs = {}
    for vp in sorted((R / "briefs").glob("*.verdict.json")):
        v = json.loads(vp.read_text())
        if "error" not in v:
            runs.setdefault(vp.name[:-len(".verdict.json")].rsplit("-", 1)[0], []).append(verdicts(truth, v))
    meta = json.loads((R / "stand.json").read_text()) if (R / "stand.json").exists() else {}
    same = [truth.get("snapshot"), truth.get("strip"), [(r["id"], r.get("rule")) for r in truth["rules"]]]
    return {"n": len(truth["rules"]), "runs": runs, "stage": truth.get("stage", "brief"), "truth": same,
            "key": meta.get("key", "documented"), "arms": meta.get("arms"), "patch": meta.get("docs_patch") or ""}, None


def share(case, arm, kinds):
    rs = case["runs"][arm]
    return sum(sum(v in kinds for v in r.values()) for r in rs) / len(rs) / case["n"]


def boot(diffs, draws):
    rng, xs, k = random.Random(1), [], len(diffs)
    for _ in range(draws):
        xs.append(sum(rng.choice(diffs) for _ in range(k)) / k)
    xs.sort()
    return xs[int(0.025 * draws)], xs[int(0.975 * draws)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("ids", nargs="*")
    ap.add_argument("--out"); ap.add_argument("--draws", type=int, default=10000)
    o = ap.parse_args()
    ids = o.ids or sorted({p.name for lab in (o.a, o.b) if stand.results_for(lab).is_dir()
                           for p in stand.results_for(lab).iterdir() if p.is_dir()})
    pairs, left = {}, []
    for cid in ids:
        (a, wa), (b, wb) = load(o.a, cid), load(o.b, cid)
        if a is None or b is None:
            left.append(f"{cid} ({o.a if a is None else o.b}: {wa if a is None else wb})"); continue
        if a["key"] != b["key"]:
            print(f"compare_runs: {cid} was judged with different keys ({o.a}: {a['key']}, {o.b}: {b['key']}): "
                  "compare runs made with the same KEY", file=sys.stderr); sys.exit(2)
        if a["truth"] != b["truth"]:   # the case was edited between the runs: rule ids no longer name the same rules
            print(f"compare_runs: {cid} has another truth in {o.a} and {o.b} (snapshot, strip list or rules): the case "
                  "changed between the runs — rerun both labels from the same case file", file=sys.stderr); sys.exit(2)
        if a["arms"] and b["arms"] and a["arms"] != b["arms"]:
            print(f"compare_runs: {cid} ran different arms ({a['arms']} / {b['arms']})", file=sys.stderr); sys.exit(2)
        pairs[cid] = (a, b)
    for side, label in ((0, o.a), (1, o.b)):   # one run is one state of the docs: a label with two patches compares nothing
        seen = {ab[side]["patch"] or "none" for ab in pairs.values()}
        if len(seen) > 1:
            print(f"compare_runs: the cases of {label} ran with different docs patches ({', '.join(sorted(seen))}): "
                  "rerun them under one docs patch, in a new RUN_LABEL", file=sys.stderr); sys.exit(2)
    key =next(iter(pairs.values()))[0]["key"] if pairs else "documented"
    out = [f"# Runs {o.a} → {o.b}\n",
           f"Cases compared: {' '.join(pairs) or 'none'} · key: {key} · 95% intervals: case bootstrap, {o.draws} draws"]
    if left:
        out.append("Left out: " + "; ".join(left))
    changes = []
    for stage in sorted({a["stage"] for a, _ in pairs.values()}):
        out += [f"\n## Stage {stage}\n", "| Arm | Cases | Provided A | Provided B | Difference | 95% | Better / worse / equal | "
                "Provided or partial A → B |", "|---|---|---|---|---|---|---|---|"]
        cs = {c: ab for c, ab in pairs.items() if ab[0]["stage"] == stage}
        for arm in sorted({arm for a, b in cs.values() for arm in a["runs"] if arm in b["runs"]}):
            both = [c for c, (a, b) in cs.items() if arm in a["runs"] and arm in b["runs"]]
            pa = [share(cs[c][0], arm, ("provided",)) for c in both]
            pb = [share(cs[c][1], arm, ("provided",)) for c in both]
            qa = [share(cs[c][0], arm, ("provided", "partial")) for c in both]
            qb = [share(cs[c][1], arm, ("provided", "partial")) for c in both]
            d = [y - x for x, y in zip(pa, pb)]
            lo, hi = boot(d, o.draws)
            m = lambda xs: sum(xs) / len(xs)
            out.append(f"| {arm} | {len(both)} | {100 * m(pa):.0f}% | {100 * m(pb):.0f}% | {100 * m(d):+.0f} pts | "
                       f"{100 * lo:+.0f} … {100 * hi:+.0f} | {sum(x > 0 for x in d)} / {sum(x < 0 for x in d)} / "
                       f"{sum(x == 0 for x in d)} | {100 * m(qa):.0f}% → {100 * m(qb):.0f}% |")
            for c in both:
                got = lambda case: {r for v in case["runs"][arm] for r, x in v.items() if x == "provided"}
                ga, gb = got(cs[c][0]), got(cs[c][1])
                if gb - ga or ga - gb:
                    changes.append(f"- {c} {arm}: gained {', '.join(sorted(gb - ga)) or 'none'}; lost {', '.join(sorted(ga - gb)) or 'none'}")
    out += ["\n## Rules gained and lost\n"] + (changes or ["- none"])
    text = "\n".join(out) + "\n"
    print(text, end="")
    if o.out:
        Path(o.out).write_text(text)


if __name__ == "__main__":
    main()
