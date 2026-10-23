#!/bin/zsh
# Judge calibration: the saved briefs of one case judged again by another model, with the same judge prompt and blinding, in
# the case's snapshot. No new sessions. The verdict sits next to the main one: RESULTS/<id>/briefs/<arm>-<run>.verdict.<model>.json
# (+ .judge.<model>.meta.json: the model ids and cost). Compare with compare_judges.py --tag <model> <ids…>.
# A brief already judged by that model without an error is skipped. The judge reads the base as the briefs' sessions saw it:
# give the run's BASE_STRIP, RESULTS, DOCS_PATCH and KEY again for its briefs.
# Usage: calibrate.sh <id> [model]     (default model: opus; PAR judges at a time)
set -u
H=${0:A:h}; source $H/lib.sh
TID=$1; MODEL=${2:-opus}
export BENCH=$BENCH_DATA/runs-calibrate; B=$BENCH${RUN_LABEL:+/$RUN_LABEL}   # as lib.sh: a label is its own subdir
export JUDGE_MODEL=$MODEL JUDGE_TAG=$MODEL
T=$TASKS/$TID.truth.json; RB=$RESULTS/$TID/briefs; LOG=$RESULTS/$TID/calibrate-$MODEL.log
[ -f $T ] || { echo "no tasks/$TID.truth.json" >&2; exit 2; }
[ -d $B/$TID ] && { echo "$B/$TID exists: move it away to rerun" >&2; exit 2; }
SNAP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['snapshot'])" $T)
mkdir -p $B/$TID
log() { echo "$(date +%T) $*" | tee -a $LOG; }
log "1 the snapshot $SNAP, judge $MODEL"
$H/prep.sh $TID $SNAP NONE >> $LOG 2>&1 || exit 2   # the base (the NONE clone is not needed)
rm -rf -- "${B:?}/${TID:?}/NONE"
log "2 judge"
todo=(); for f in $RB/*.brief.md(N); do
  ar=${${f:t}%.brief.md}
  [ -s $RB/$ar.verdict.$MODEL.json ] && ! grep -q '"error"' $RB/$ar.verdict.$MODEL.json && continue
  [ -s $RB/$ar.verdict.json ] || continue   # only briefs the main judge graded
  todo+=($ar)
done
n=0; for ar in $todo; do
  mkdir -p $B/$TID/out/$ar && cp $RB/$ar.brief.md $B/$TID/out/$ar/brief.md
  $H/judge.sh $TID $ar > $B/$TID/out/$ar/judge.line 2>&1 & n=$((n+1)); sleep 2; [ $((n % PAR)) -eq 0 ] && wait
done; wait
for ar in $todo; do
  O=$B/$TID/out/$ar; cat $O/judge.line | tee -a $LOG
  grep -q '"error"' $O/verdict.$MODEL.json 2>/dev/null && { log "   judge error on $ar: not kept"; continue; }
  cp $O/verdict.$MODEL.json $RB/$ar.verdict.$MODEL.json
  python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(json.dumps({'models': sorted(r.get('modelUsage') or {}), 'cost_usd': r.get('total_cost_usd')}))" \
    $O/judge.$MODEL.json > $RB/$ar.judge.$MODEL.meta.json
done
rm -rf -- "${B:?}/${TID:?}"
log "done: ${#todo} briefs"
