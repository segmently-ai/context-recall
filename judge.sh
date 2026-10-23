#!/bin/zsh
# Blinded judge (isolated, read-only) for one brief. Usage: judge.sh <tid> <arm-run>
# Env: JUDGE_MODEL (default: stand.env), JUDGE_TAG (writes judge.<tag>.json / verdict.<tag>.json, so a calibration run keeps the
# default verdicts)
set -u
H=${0:A:h}; source $H/lib.sh
TID=$1; AR=$2; OUT=$B/$TID/out/$AR; T=${JUDGE_TAG:+.$JUDGE_TAG}
# the blinding words: every adapter's ARM_<F>_BLIND (all adapters, not only this case's arms), then any MCP tool name
WORDS=(); for _a in $H/arms/*.zsh(N) ${OWN_ARMS:+$OWN_ARMS/*.zsh(N)}; do _v=ARM_${${_a:t:r}}_BLIND; [ -n "${(P)_v:-}" ] && WORDS+=(${(P)_v}); done
WORDS+=('mcp__\w+')
python3 - $H $TID $OUT "${(j:|:)WORDS}" $TASKS <<'PY'
import json, re, sys
from pathlib import Path
h, tid, out, words, tasks = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
truth = json.loads((tasks / f"{tid}.truth.json").read_text())
brief = (out / "brief.md").read_text()
# blind: drop tool names and the tool's own skill/CLI words
blind = re.sub(r"(?i)\b(" + words + r")\b", "[tool]", brief)
def src(r):
    if not r.get("sources") and not r.get("doc"):   # KEY=all: a rule no doc held at the snapshot
        return "none (not written in any doc at the snapshot)"
    ss = r.get("sources") or [{"doc": r["doc"], "line": r.get("line")}]
    return ", ".join(f"`{x['doc']}{':' + str(x['line']) if x.get('line') else ''}`" for x in ss)
NO_SOURCE = ("\n\nA rule with no source was not written in any doc at the snapshot. Grade it `provided` when the brief states "
             "it and points to a document of this repository that states it (read that document to check); `partial` when "
             "the brief states it with no such document.")
def text(r):
    t = r.get("texts") or [r.get("rule") or r["quote"]]
    return t[0] if len(t) == 1 else " | ".join(f"({k}) {x}" for k, x in enumerate(t, 1))
rules = "\n".join(f"- {r['id']}: {text(r)} — {'source' if len(r.get('sources') or [1]) == 1 else 'sources'}: {src(r)} — why it applies: {r['why']}" for r in truth["rules"])
p = (h / "judge-prompt.md").read_text().replace("{{REQUEST}}", (tasks / f"{tid}.request.txt").read_text().strip())
if any(not r.get("sources") and not r.get("doc") for r in truth["rules"]):
    rules += NO_SOURCE
p = p.replace("{{RULES}}", rules).replace("{{BRIEF}}", blind)
(out / "judge-input.md").write_text(p)
PY
cd $B/$TID/base
claude -p "$(cat $OUT/judge-input.md)" --model $JUDGE_MODEL --output-format json \
  --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --permission-mode dontAsk --allowedTools Read Grep Glob --disallowedTools Bash WebFetch WebSearch \
  > $OUT/judge$T.json 2> $OUT/judge$T.stderr
python3 - $OUT "$T" <<'PY'
import json, re, sys
from pathlib import Path
out, t = Path(sys.argv[1]), sys.argv[2]
try:   # no JSON at all (the call died, an empty reply): an error verdict, not a crash
    r = json.loads((out / f"judge{t}.json").read_text())
except (OSError, json.JSONDecodeError) as e:
    r = {"is_error": True, "result": f"no judge reply ({e})"}
txt = r.get("result", ""); m = re.search(r"\{.*\}", txt, re.S)
# a failed call (r["is_error"]: e.g. "You've hit your session limit") is an error verdict, never an all-absent one
v = {"error": txt[:300]}
if m and not r.get("is_error"):
    try:
        v = json.loads(m.group(0))
    except json.JSONDecodeError as e:   # malformed JSON from the judge: an error verdict, not a crash
        v = {"error": f"unparsed judge JSON ({e}): {txt[:240]}"}
(out / f"verdict{t}.json").write_text(json.dumps(v, indent=1, ensure_ascii=False))
mk = v.get("must_know", []); ex = v.get("extra_rules", [])
print(out.name, "| must-know:", [f"{x['id']}={x['verdict']}" for x in mk],
      "| extras applies/noise:", sum(x["verdict"] == "applies" for x in ex), "/", sum(x["verdict"] == "noise" for x in ex),
      "| unsupported:", len(v.get("unsupported", [])), "| judge $%.2f" % (r.get("total_cost_usd") or 0),
      *(["| JUDGE ERROR:", v["error"][:120]] if "error" in v else []))
sys.exit(1 if "error" in v else 0)
PY
