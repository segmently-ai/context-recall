#!/bin/zsh
# The stand's entry point.
#   bench.sh setup                 build and check the stand (setup.sh)
#   bench.sh case <id> [--clean] [--resume]
#                                  one case end to end: case2task.py, then cycle.sh (~20–40 min; run it in the background);
#                                  --clean deletes the case's snapshot clones once results/<id>/summary.md is written;
#                                  under RUN_LABEL a case the label already holds is refused unless --resume
#   bench.sh summary <id>          rebuild results/<id>/summary.md (works after the clones are gone)
#   bench.sh clean <id>            delete the case's snapshot clones (the results stay)
#   bench.sh status                the stand's manifest, the cases and which have results
# A case is cases/<id>-<slug>.case.json (or cases/<id>.case.json); its id is the file name up to the first "-".
# Env overrides any key of stand.env (JUDGE_MODEL=opus, RUNS=3, ARMS=BARE,TRAIL …).
set -u
H=${0:A:h}; source $H/lib.sh
SUMMARY=${SUMMARY:-summary.py}
case_file() { local f=($CASES/$1-*.case.json(N) $CASES/$1.case.json(N)); [ ${#f} -eq 1 ] || { echo "no single case file for $1" >&2; exit 2; }; echo $f; }
clean_case() {   # every snapshot clone of the case (each carries the base's .bench-base-ok); out/ and the logs stay
  local d; for d in $B/${1:?}/*(N/); do [ -f $d/.bench-base-ok ] && rm -rf -- "${d:?}"; done; df -h ~ | tail -1
}
case ${1:-} in
  setup) exec $H/setup.sh ;;
  case)
    TID=$2; F=$(case_file $TID) || exit 2; shift 2; RESUME=0   # case_file's exit ends only its subshell
    for o in $@; do case $o in --clean) export CLEAN=1 ;; --resume) RESUME=1 ;; *) echo "unknown option $o" >&2; exit 2 ;; esac; done
    if [ -n "${RUN_LABEL:-}" ] && (( ! RESUME )) && { [ -e $RESULTS/$TID ] || [ -e $B/$TID/out ]; }; then
      echo "run label $RUN_LABEL already has case $TID ($RESULTS/$TID): choose another RUN_LABEL, or --resume to continue it" >&2; exit 2
    fi
    python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['verdict']=='reject')" $F || { echo "$TID is a rejected case" >&2; exit 2; }
    SNAP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['snapshot'])" $F)
    git -C $HOST_REPO cat-file -e "$SNAP^{commit}" 2>/dev/null || { echo "the snapshot $SNAP of $TID is not a commit of $HOST_REPO" >&2; exit 2; }
    same_run $RESULTS/$TID || exit 2   # before case2task.py rewrites the run's truth
    python3 $H/case2task.py $F $TID || exit 2
    exec $H/cycle.sh $TID ;;
  summary) python3 $H/$SUMMARY $2 > $RESULTS/$2/summary.md && cat $RESULTS/$2/summary.md ;;
  clean) clean_case $2 ;;
  status)
    [ -f $BENCH_DATA/stand.json ] && cat $BENCH_DATA/stand.json || echo "stand not built (bench.sh setup)"
    for f in $CASES/*.case.json(N); do
      id=${f:t:r:r}; tid=${id%%-*}
      v=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['verdict'])" $f)
      r=$([ -s $RESULTS/$tid/summary.md ] && echo "results $(date -r $RESULTS/$tid/summary.md +%F)" || echo "-")
      s=$([ -d $B/$tid/base ] && echo "clones $(du -sh $B/$tid 2>/dev/null | cut -f1)" || echo "")
      printf '%-44s %-7s %-18s %s\n' $id $v "$r" "$s"
    done ;;
  *) sed -n '2,11p' $0; exit 2 ;;
esac
