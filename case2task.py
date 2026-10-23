"""Turns a reference case (cases/<id>.case.json) into the bench's task files: tasks/<tid>.request.txt (the case's
REQUEST_FIELD, default request_en) and tasks/<tid>.truth.json (code, tests, rules with an exact quote from the doc at the
snapshot, so score.py can see a sighting). A graded rule is a family (the rules' `family` key): one id F<n> with every source of
its member rules, each source with its quote; rules with a `drop` key are left out. A file the real change edited is a test
when a part of its path is in TEST_DIRS (comma-separated), else code; .md files are neither. The case's optional areas
(truth.areas_modify / areas_reference: the parts of the repository the change edits or only reads) are carried over under
the case's own key when present. LEGACY_IDS=1 adds
`legacy_ids`: the v1 ids (R<n>, one per rule with a first-source quote), so verdicts written before the families can be
restated. Usage: python3 case2task.py <case.json> <tid>"""
import json, re, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402
NORM = re.compile(r"\s+")
REF = re.compile(r"([\w./@-]+\.md):(\d+)(?:[-–](\d+))?")
norm = lambda s: NORM.sub(" ", s.replace("`", "").replace("*", "")).strip().lower()
c = json.loads(Path(sys.argv[1]).read_text()); tid = sys.argv[2]
snap = c["snapshot"]
REQUEST_FIELD = stand.cfg("REQUEST_FIELD", "request_en")
TEST_DIRS = {d for d in stand.cfg("TEST_DIRS", "__tests__,tests,test").split(",") if d}
LEGACY = stand.cfg("LEGACY_IDS") == "1"
is_test = lambda p: bool(TEST_DIRS & set(p.split("/")[:-1]))
_docs = {}
def doc_lines(doc):
    if doc not in _docs:
        r = subprocess.run(["git", "-C", str(stand.HOST), "show", f"{snap}:{doc}"], capture_output=True, text=True)
        _docs[doc] = r.stdout.split("\n") if r.returncode == 0 else None
    return _docs[doc]
def quote_at(doc, a, b, widen=True):
    """The longest line of the range that is found in the doc. A one-line ref is often a short heading: then the rule's body
    is searched too (up to six lines, never past the next heading, never inside a code fence), and the heading itself is the
    quote when the body has no prose line. widen=False is the v1 search, used only to number legacy ids."""
    lines = doc_lines(doc)
    if lines is None:
        return None
    full = norm("\n".join(lines))
    rng = list(range(a - 1, b))
    if widen and a == b:
        fence = [False] * len(lines); f = False
        for k, l in enumerate(lines):
            if l.lstrip().startswith("```"):
                f = not f; fence[k] = True
            else:
                fence[k] = f
        rng = [a - 1]
        for k in range(a, min(a + 6, len(lines))):
            if lines[k].lstrip().startswith("#"):
                break
            if not fence[k]:
                rng.append(k)
    cands = [lines[k].strip().lstrip("-*>|# ").strip() for k in rng if k < len(lines)]
    found = [x for x in cands if norm(x)[:60] in full]
    best = sorted((x for x in found if len(norm(x)) >= 40), key=len, reverse=True)
    if best:
        return best[0]
    if widen and found and len(norm(found[0])) >= 20:
        return found[0]
    return None

items, v1 = {}, 0
for i, r in enumerate(c["must_know_rules"], 1):
    refs = [(m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))) for m in REF.finditer(r["source"])]
    if not refs:
        continue
    legacy = None
    if quote_at(*refs[0], widen=False):
        v1 += 1; legacy = f"R{v1}"
    if r.get("drop"):
        continue
    sources = [{"doc": d, "line": a, "quote": q[:220]} for d, a, b in refs if (q := quote_at(d, a, b))]
    if not sources:
        print("no quote for", r["source"]); continue
    key = r.get("family") or f"rule{i}"
    it = items.setdefault(key, {"texts": [], "sources": [], "why": [], "legacy_ids": [], "case_rules": []})
    it["texts"].append(r["rule"]); it["why"].append(r["why"]); it["case_rules"].append(i)
    if legacy:
        it["legacy_ids"].append(legacy)
    it["sources"] += [s for s in sources if (s["doc"], s["line"]) not in {(x["doc"], x["line"]) for x in it["sources"]}]
rules = []
for n, it in enumerate(items.values(), 1):
    first = it["sources"][0]
    rule = {"id": f"F{n}", "rule": " / ".join(it["texts"]), "texts": it["texts"], "why": " / ".join(it["why"]),
            "doc": first["doc"], "line": first["line"], "quote": first["quote"], "sources": it["sources"]}
    if LEGACY:
        rule["legacy_ids"] = it["legacy_ids"]
    rule["case_rules"] = it["case_rules"]
    rules.append(rule)
if not rules and c.get("verdict") != "reject":   # an empty key would grade nothing and look like a clean run
    print(f"case2task: no rule of {c['id']} could be quoted at {snap}: check the snapshot and every doc:line", file=sys.stderr)
    sys.exit(2)
if stand.cfg("KEY", "documented") == "all":   # a calibration's wider key: the rules no doc held at the snapshot, too
    for n, u in enumerate(c.get("undocumented_rules") or [], 1):
        rules.append({"id": f"U{n}", "rule": u["rule"], "texts": [u["rule"]],
                      "why": f"the change respected it ({u.get('where_in_code', '')})", "doc": "", "line": None,
                      "quote": u["rule"], "sources": [], "case_rules": []})
code = [f["path"] for f in c["truth"]["files_edit"] if not f["path"].endswith(".md") and not is_test(f["path"])]
tests = [f["path"] for f in c["truth"]["files_edit"] if f["path"] not in code and not f["path"].endswith(".md")]
truth = {"code": code, "tests": tests, "created": [], "acceptable": [f["path"] for f in c["truth"]["files_read"]],
         "rules": rules}
for key in ("areas_modify", "areas_reference", "modules_modify", "modules_reference"):   # the case's areas, when it names
    if key in c["truth"]:                                                                  # them, under the case's own key
        truth[key] = c["truth"][key]
truth.update({"docs_must_read": [d["doc"] for d in c["truth"]["docs_must_read"]], "snapshot": snap, "case": c["id"]})
# a staged case: its stage, its feature, what the stage received (the reworked text only), the rules its input already states
if c.get("stage"):
    truth["stage"] = c["stage"]
if c.get("group"):
    truth["group"] = c["group"]
if c.get("inputs"):
    truth["inputs"] = [{"label": i["label"], "text": i["text"]} for i in c["inputs"]]
if c.get("given_rules"):
    truth["given_rules"] = [{"rule": r["rule"], "source": r["source"]} for r in c["given_rules"]]
if c.get("seed"):
    truth["seeded"] = True
if c.get("strip"):   # the task's own text in the snapshot (its task file, the feature's spec): prep.sh removes it
    truth["strip"] = c["strip"]
stand.TASKS.mkdir(parents=True, exist_ok=True)
(stand.TASKS / f"{tid}.truth.json").write_text(json.dumps(truth, indent=1, ensure_ascii=False))
request = c[REQUEST_FIELD].strip()
for i in c.get("inputs") or []:   # a staged case: what the stage received, under its own heading (the reworked text)
    request += f"\n\n## {i['label']}\n{i['text'].strip()}"
seed = c.get("seed")   # the seeded path: what the operator already named, the same for every arm
if seed:
    lines = ([seed["text"].strip()] if seed.get("text", "").strip() else []) + [f"- {p}" for p in seed.get("paths", [])]
    request += "\n\nWhat the operator already knows:\n" + "\n".join(lines)
(stand.TASKS / f"{tid}.request.txt").write_text(request + "\n")
print(tid, "rules", len(rules), "sources", sum(len(r["sources"]) for r in rules), "code", len(code), "tests", len(tests))
