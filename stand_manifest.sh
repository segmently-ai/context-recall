#!/bin/zsh
# Prints what the stand is made of, as JSON: the config, the tool versions found, each arm family's own part (its
# arm_manifest_<F>: versions, pins, builds) and the harness revision. cycle.sh writes it to results/<tid>/stand.json; setup.sh
# to $BENCH_DATA/stand.json. Compare two manifests before you compare two results.
H=${0:A:h}; source $H/lib.sh
tree_hash() { [ -d $1 ] && (cd $1 && find . -type f -not -name '*.pyc' -not -path '*/__pycache__/*' | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256 | cut -c1-16) || echo missing; }
{
  python3 -c 'import json,sys; a = sys.argv[1:]
print(json.dumps({"date": a[0], "harness": {"stand_head": a[1], "stand_dirty": a[2] == "dirty", "stand_tree": a[3]},
  "host": a[4], "arms": a[5].split(","), "tools": {"claude": a[6]}, "pins": {"claude": a[7]},
  "models": {"brief": a[8], "judge": a[9]}, "runs": {"per_arm": a[10]}, "key": a[11], "docs_patch": a[12]}))' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git -C $STAND rev-parse --short HEAD 2>/dev/null)" \
    "$([ -z "$(git -C $STAND status --porcelain -- $STAND 2>/dev/null)" ] && echo clean || echo dirty)" "$(tree_hash $STAND)" \
    "$HOST_REPO" "$ARMS" "$(claude --version 2>/dev/null | head -1)" "${CLAUDE_VERSION:-}" "$BRIEF_MODEL" "$JUDGE_MODEL" "$RUNS" \
    "${KEY:-documented}" "$(patch_id)"
  for f in $(arm_families $ARM_LIST); do has_hook arm_manifest $f && arm_manifest_$f; done
} | python3 -c 'import json,sys
def merge(a, b):
    for k, v in b.items():
        a[k] = merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a
out = {}
for line in sys.stdin:
    if line.strip():
        merge(out, json.loads(line))
print(json.dumps(out, indent=1))'
