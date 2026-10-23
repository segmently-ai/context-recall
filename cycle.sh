#!/bin/zsh
# The brief-only cycle for one case (stage 1: what the tool puts in front of the agent before it plans):
#   1 prep the snapshot and one clone per arm (prep.sh) · 2 build the arms' indexes (build.sh)
#   3 every arm writes a brief, its runs each (RUNS, or the adapter's arm_runs_<F>), PAR sessions at a time
#   4 deterministic score (score.py) + blinded judge (judge.sh, JUDGE_MODEL) on every brief
#   5–6 the arm families' own post-steps, when an adapter has them (arm_post_<F>: e.g. a check run on every brief)
#   7 RESULTS/<tid>/: stand.json, briefs/<arm>-<run>.{brief.md,score.json,verdict.json}, the families' extra files
#     (arm_collect_<F>), summary.md (SUMMARY)
#   8 CLEAN=1: delete the case's snapshot clones once the summary is written (the results stay)
# Usage: cycle.sh <tid>   (tasks/<tid>.truth.json and .request.txt from case2task.py)
# Env: any key of stand.env (ARMS, RUNS, PAR, the models, BASE_STRIP, SUMMARY), BENCH and RESULTS (an ablation's own run and
# results dirs), FROM (the step to start at), CLEAN (1 = step 8)
set -u
H=${0:A:h}; source $H/lib.sh; stand_ready || exit 2
TID=$1; FROM=${FROM:-1}; SUMMARY=${SUMMARY:-summary.py}
T=$TASKS/$TID.truth.json; REQ=$TASKS/$TID.request.txt
SNAP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['snapshot'])" $T)
R=$RESULTS/$TID; mkdir -p $R/briefs
log() { echo "$(date +%T) $*" | tee -a $R/cycle.log; }
ALL=(); ACTIVE=(); MAXR=0   # ALL: every session <arm>-<run>, run by run; ACTIVE: the arms with at least one session
for a in $ARM_LIST; do n=$(arm_runs $a); (( n > 0 )) && ACTIVE+=($a); (( n > MAXR )) && MAXR=$n; done
for run in $(seq 1 $MAXR); do for a in $ACTIVE; do (( run <= $(arm_runs $a) )) && ALL+=("$a-$run"); done; done
FAMS=($(arm_families $ACTIVE))

same_run $R || exit 2
$H/stand_manifest.sh > $R/stand.json   # what this run was made of (the config, the tool versions, the builds)
if [ $FROM -le 1 ]; then
  log "1 prep $TID at $SNAP${DOCS_PATCH:+ with the docs patch $DOCS_PATCH}"; $H/prep.sh $TID $SNAP $ACTIVE >> $R/cycle.log 2>&1; rc=$?
  # 3: the docs patch did not apply to this snapshot — the case is left out of the run (prep wrote excluded.txt)
  (( rc == 3 )) && { log "excluded: $(cat $R/excluded.txt)"; exit 0; }
  (( rc == 2 )) && { log "prep refused (see cycle.log)"; exit 2; }
fi
if [ $FROM -le 2 ]; then log "2 build"; $H/build.sh $TID $ACTIVE; tail -2 $B/$TID/build.log >> $R/cycle.log 2>/dev/null; fi
if [ $FROM -le 3 ]; then
  log "3 briefs: ${#ALL} sessions (${ACTIVE[*]})"; n=0
  REUSED=(); for ar in $ALL; do [ -e $B/$TID/out/$ar ] && REUSED+=($ar); done
  (( ${#REUSED} )) && log "   reused, not run again: ${REUSED[*]} (earlier output in $B/$TID/out/; delete a session's dir to rerun it)"
  for ar in $ALL; do
    a=${ar%-*}; r=${ar##*-}; [ -e $B/$TID/out/$ar ] && continue
    $H/run.sh $TID $a $r $REQ >> $R/cycle.log 2>&1 &
    n=$((n+1)); sleep 3; [ $((n % PAR)) -eq 0 ] && wait
  done; wait
fi
if [ $FROM -le 4 ]; then
  log "4 score + judge ($JUDGE_MODEL)"
  python3 $H/score.py $TID $ALL > $R/score.txt 2>&1
  n=0; for ar in $ALL; do $H/judge.sh $TID $ar >> $R/judge.txt 2>&1 & n=$((n+1)); sleep 2; [ $((n % PAR)) -eq 0 ] && wait; done; wait
fi
for f in $FAMS; do has_hook arm_post $f && arm_post_$f; done
log "7 collect"
for ar in $ALL; do
  O=$B/$TID/out/$ar; [ -d $O ] || continue
  for f in brief.md score.json verdict.json; do cp $O/$f $R/briefs/$ar.$f 2>/dev/null; done
done
for f in $FAMS; do has_hook arm_collect $f && arm_collect_$f; done
python3 $H/$SUMMARY $TID > $R/summary.md 2>&1; log "done"; cat $R/summary.md
if [ "${CLEAN:-}" = 1 ] && [ -s $R/summary.md ] && ! grep -q Traceback $R/summary.md; then
  log "8 clean: snapshot clones of $TID"
  for d in $B/$TID/*(N/); do [ -f $d/.bench-base-ok ] && rm -rf -- "${d:?}"; done
  df -h ~ | tail -1 | tee -a $R/cycle.log
fi
