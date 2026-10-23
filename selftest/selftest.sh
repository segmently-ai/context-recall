#!/bin/zsh
# The kit's self-test on a synthetic repository, run the way the plugin runs it: the kit stays read-only, everything goes to
# a workspace in the demo repository (skills/context-recall/scripts/workspace.py init) under RUN_LABEL=selftest.
#   the demo repository (make_demo_repo.sh: a small service, five docs of rules, three tasks written as task files before
#   their work), the history adapter over its task files, the golden cases (selftest/cases/, one of them seeded), then every
#   step a user takes — validate_case.py, bench.sh setup, bench.sh case <id> --clean for each case, stats.py,
#   calibrate.sh + compare_judges.py — and the checks of check.py. Your own stand.env, cases and results are never touched.
#   default   a stand-in claude (selftest/bin/claude): no model call, no cost; the arms' real tools are installed or
#             checked and their indexes really built — it tests the harness end to end
#   --real    the real claude, without steps 7–8: RUNS sessions per arm per case plus one judge call each — by default
#             7 cases × 4 arms = 28 sessions + 28 judge calls (~$7 API-equivalent, drawn from your plan's limits);
#             --cases d01,d02,d03: 12 sessions + 12 judge calls (~$3)
# Options: --cases d01,d02 · --arms BARE,TRAIL · --own-arms <workspace>/arms (your own, from workspace.py add-arm) · --keep
#          (keep the temp folder) · env SELFTEST_DIR (the folder),
#          SELFTEST_DATA (reuse a data dir: skips the Trail install; the runs are always fresh), RUNS (default 1)
# Exit 0 = every check passed.
set -u
S=${0:A:h}; H=${S:h}
OWN=""; REAL=0; KEEP=0; CASES=(d01 d02 d02s d03 f1spec f1arch f1t1); ARMS_ST=BARE,SERENA,GRAPHIFY,TRAIL
while (( $# )); do
  case $1 in
    --real) REAL=1 ;; --keep) KEEP=1 ;;
    --cases) CASES=(${(s:,:)2}); shift ;; --arms) ARMS_ST=$2; shift ;; --own-arms) OWN=${2:A}; shift ;;
    *) sed -n '2,16p' $0; exit 2 ;;
  esac; shift
done
ST_RUNS=${RUNS:-1}
W=${SELFTEST_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/stand-selftest.XXXXXX")}
DATA=${SELFTEST_DATA:-$W/data}
[ -e $W/repo ] && { echo "$W/repo exists: give an empty SELFTEST_DIR" >&2; exit 2; }
say() { print -r -- "== $*"; }
fails=()
TPL=$H/stand.env.example; [ -f $TPL ] || TPL=$H/stand.env.template
for k in ${(f)"$(sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' $TPL)"} BENCH RESULTS BENCH_WORKSPACE RUN_LABEL KEY DOCS_PATCH; do
  unset $k   # your environment never leaks in
done
export PYTHONDONTWRITEBYTECODE=1   # the kit stays read-only, as in a plugin install

say "1 the demo repository and its workspace"
mkdir -p $W && $S/make_demo_repo.sh $W/repo || exit 2
python3 $H/skills/context-recall/scripts/workspace.py init --repo $W/repo || exit 2
WS=$W/repo/.context-recall
sed -i.bak -e "s#^BENCH_DATA=.*#BENCH_DATA=$DATA#" -e "s#^ARMS=.*#ARMS=$ARMS_ST#" -e "s#^RUNS=.*#RUNS=$ST_RUNS#" $WS/stand.env && rm -f $WS/stand.env.bak
cp $S/cases/*.case.json $WS/cases/
if [ -n "$OWN" ]; then   # the user's own arms (workspace.py add-arm), beside the workspace as in theirs
  mkdir -p $WS/arms && cp $OWN/*.zsh(N) $OWN/integration-*.md(N) $WS/arms/ || exit 2
fi
export BENCH_WORKSPACE=$WS RUN_LABEL=selftest BENCH=$W/runs   # the runs always fresh: a reused data dir shares only its tools
(( REAL )) || export PATH=$S/bin:$PATH

say "2 the history adapter"
n=$(python3 $H/history/taskfiles.py --repo $W/repo --glob 'tasks/*.md' --json | python3 -c "import json,sys;print(len(json.load(sys.stdin)['records']))")
[ "$n" = 3 ] && echo "taskfiles: 3 candidates" || { echo "taskfiles: $n candidates, expected 3"; fails+=(history); }
python3 $H/history/speckit.py --repo $W/repo --out $W/features > /dev/null
n=$(python3 $H/history/staged.py --dir $W/features --json | python3 -c "import json,sys;print(' '.join(r['stage'] for r in json.load(sys.stdin)['records']))")
[ "$n" = "spec architecture task task" ] && echo "staged: spec, architecture, 2 tasks" || { echo "staged: '$n'"; fails+=(staged); }
say "3 validate_case.py"; python3 $H/validate_case.py $WS/cases/*.case.json || fails+=(validate)
say "4 bench.sh setup (data: $DATA)"; $H/bench.sh setup > $W/setup.log 2>&1 || { fails+=(setup); tail -5 $W/setup.log; }
grep -E 'warning|^(trail|graphify|serena|claude) ' $W/setup.log
for c in $CASES; do
  say "5 bench.sh case $c --clean"
  $H/bench.sh case $c --clean > $W/case-$c.log 2>&1 || { fails+=(case-$c); tail -5 $W/case-$c.log; }
done
say "6 stats.py --by stage"; python3 $H/stats.py --ref BARE --by stage $CASES > $W/stats.md 2>&1 || fails+=(stats)
grep -E '^(## Stage|\| BARE \|)' $W/stats.md
if (( ! REAL )); then
  say "7 calibrate.sh + compare_judges.py (the stand-in as the second judge)"
  { $H/calibrate.sh ${CASES[1]} standin > $W/calibrate.log 2>&1 && python3 $H/compare_judges.py --tag standin ${CASES[1]} > $W/compare.md 2>&1 \
    && sed -n '3,4p' $W/compare.md; } || fails+=(calibrate)
fi
if (( ! REAL )); then
  say "8 calibration: d01 with and without the docs patch (selftest/docs-v2.patch writes its undocumented rule), KEY=all"
  { KEY=all RUN_LABEL=cal-a $H/bench.sh case d01 --clean > $W/cal-a.log 2>&1 \
    && KEY=all RUN_LABEL=cal-b DOCS_PATCH=$S/docs-v2.patch $H/bench.sh case d01 --clean > $W/cal-b.log 2>&1 \
    && python3 $H/compare_runs.py cal-a cal-b d01 --draws 200 > $W/compare-runs.md 2>&1; } || fails+=(calibration)
  for a in ${(s:,:)ARMS_ST}; do
    grep -q "^- d01 $a: gained U1; lost none" $W/compare-runs.md && echo "$a: gained U1" || { echo "$a: U1 not gained"; fails+=(calibration-$a); }
  done
fi
say "9 checks"
python3 $S/check.py $WS $BENCH $REAL $CASES || fails+=(checks)
[ -z "$(git -C $W/repo status --porcelain)" ] || { echo "the demo repository is not clean after the run"; fails+=(repo-clean); }
if (( ${#fails} )); then
  print -r -- "self-test FAILED at: ${fails[*]} — logs and results kept in $W"; exit 1
fi
if (( KEEP )) || [ -n "${SELFTEST_DIR:-}" ]; then print -r -- "kept: $W"; else rm -rf -- "${W:?}"; fi
exit 0
