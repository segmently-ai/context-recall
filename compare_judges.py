"""The main judge's verdicts against another model's on the same saved briefs (calibrate.sh). Per rule item: the 4-way
agreement, provided against not, Cohen's kappa, the confusion table; per arm: items provided and provided-or-partial under
each judge, so a reader sees whether the ranking and the gaps between arms move with the judge.
Only briefs that have both verdicts, neither an error, count. Usage: compare_judges.py [--tag <model>] <id>…  (default tag opus)"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402

RANK = {"provided": 3, "partial": 2, "wrong": 1, "absent": 0}
V = ["provided", "partial", "absent", "wrong"]


def fam(truth, v):
    raw = {x["id"]: x["verdict"] for x in v.get("must_know", [])}
    out = {}
    for r in truth["rules"]:
        vs = [raw[x] for x in [r["id"]] + r.get("legacy_ids", []) if x in raw]
        out[r["id"]] = max(vs, key=lambda q: RANK.get(q, -1)) if vs else "absent"
    return out


def kappa(pairs, cats):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in cats) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--tag", default="opus")
    a = ap.parse_args()
    main_judge, tag = stand.cfg("JUDGE_MODEL", "main"), a.tag
    pairs, per = [], {}
    for tid in a.ids:
        truth = json.loads((stand.TASKS / f"{tid}.truth.json").read_text())
        for o in sorted((stand.RESULTS / tid / "briefs").glob(f"*.verdict.{tag}.json")):
            ar = o.name[:-len(f".verdict.{tag}.json")]; s = o.with_name(f"{ar}.verdict.json")
            if not s.exists():
                continue
            sv, ov = json.loads(s.read_text()), json.loads(o.read_text())
            if "error" in sv or "error" in ov:
                continue
            fs, fo = fam(truth, sv), fam(truth, ov)
            pairs += [(fs[k], fo[k]) for k in fs]
            P = per.setdefault(ar.rsplit("-", 1)[0], {"n": 0, "rules": 0, "s_prov": 0, "o_prov": 0, "s_pp": 0, "o_pp": 0})
            P["n"] += 1; P["rules"] += len(fs)
            P["s_prov"] += sum(x == "provided" for x in fs.values()); P["o_prov"] += sum(x == "provided" for x in fo.values())
            P["s_pp"] += sum(x in ("provided", "partial") for x in fs.values())
            P["o_pp"] += sum(x in ("provided", "partial") for x in fo.values())
    if not pairs:
        raise SystemExit(f"no brief has both verdicts (verdict.json and verdict.{tag}.json)")
    bin_ = [(x == "provided", y == "provided") for x, y in pairs]
    print(f"## {main_judge} (main judge) against {tag}: {len(pairs)} rule verdicts, {sum(p['n'] for p in per.values())} briefs, "
          f"cases {' '.join(a.ids)}\n")
    print(f"- 4-way agreement {sum(x == y for x, y in pairs) / len(pairs):.2f}, kappa {kappa(pairs, V):.2f}")
    print(f"- provided against not: agreement {sum(x == y for x, y in bin_) / len(bin_):.2f}, kappa {kappa(bin_, [True, False]):.2f}\n")
    c = Counter(pairs)
    print(f"| {main_judge} ↓ / {tag} → | " + " | ".join(V) + " |\n|---|" + "---|" * len(V))
    for s in V:
        print(f"| {s} | " + " | ".join(str(c[(s, o)]) for o in V) + " |")
    print(f"\n| Arm | Briefs | Provided: {main_judge} | {tag} | Provided or partial: {main_judge} | {tag} |\n|---|---|---|---|---|---|")
    for arm, P in sorted(per.items()):
        pc = lambda x: f"{100 * x / P['rules']:.0f}%"
        print(f"| {arm} | {P['n']} | {pc(P['s_prov'])} | {pc(P['o_prov'])} | {pc(P['s_pp'])} | {pc(P['o_pp'])} |")


if __name__ == "__main__":
    main()
