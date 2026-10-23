# Sourced by every stand script (zsh): the config (stand.env), the paths and the arm adapters (arms/*.zsh). Nothing here
# depends on a session.
#   STAND       this directory (the harness, the cases, the results)
#   HOST_REPO   the git repository the cases come from (stand.env; default: the repository that holds the stand)
#   BENCH_DATA  the stand's data, outside the repository: tools, snapshots and run output (default ~/.context-tools-bench)
#   B           $BENCH_DATA/runs — one directory per case: the snapshot, a clone per arm, out/<arm>-<run>/ (BENCH overrides it)
#   WORKSPACE   the user's side (BENCH_WORKSPACE; default: the stand itself): stand.env, cases/ (CASES), tasks/ (TASKS),
#               results/ — so the scripts may live in a read-only place (a plugin) and a user's data elsewhere
#   RESULTS     where a case's results go (default $WORKSPACE/results; a relative path is relative to the workspace)
#   ARM_LIST    the arms of a cycle (ARMS in stand.env, comma-separated). An arm's family is its name up to the first "-"
#               (TRAIL-V2 → TRAIL); the family's adapter arms/<FAMILY>.zsh says how to prepare, index and run it.
STAND=${STAND:-${${(%):-%x}:A:h}}
_spaced() { [[ $2 == *[[:space:]]* ]] && { echo "the stand cannot run on a path with whitespace: $1='$2'" >&2; exit 2; }; return 0; }
_spaced BENCH_WORKSPACE "${BENCH_WORKSPACE:-}"
WORKSPACE=${BENCH_WORKSPACE:-$STAND}
[ -f $WORKSPACE/stand.env ] || { echo "no $WORKSPACE/stand.env: copy stand.env.example to stand.env and fill it in" >&2; exit 2; }
# stand.env gives the defaults; a variable already set in the environment wins (JUDGE_MODEL=opus ./bench.sh case c01)
while IFS= read -r _l; do
  # a value is one word: text after whitespace that is not a comment would be cut off silently, so it is refused
  [[ $_l =~ '^([A-Za-z_][A-Za-z0-9_]*)=[^[:space:]#]*[[:space:]]+[^[:space:]#]' ]] \
    && { echo "stand.env: the value of ${match[1]} has whitespace (a value is one word; a path must have no spaces)" >&2; exit 2; }
  if [[ $_l =~ '^([A-Za-z_][A-Za-z0-9_]*)=([^[:space:]#]*)' ]] && [ -z "${(P)match[1]+x}" ]; then typeset -g "${match[1]}=${match[2]}"; fi
done < $WORKSPACE/stand.env
_home() { [[ $1 == '~'* ]] && print -r -- "$HOME${1#\~}" || print -r -- "$1"; }
HOST_REPO=$(_home "${HOST_REPO:-$(git -C $STAND rev-parse --show-toplevel)}")
BENCH_DATA=$(_home "${BENCH_DATA:-$HOME/.context-tools-bench}")
# RUN_LABEL: a run's own results and sessions (results/<label>/, runs/<label>/), so a new run never meets an old one's out/
[[ ${RUN_LABEL:-} == *[/[:space:]]* ]] && { echo "RUN_LABEL must be one plain word (no / and no whitespace): '$RUN_LABEL'" >&2; exit 2; }
B=${BENCH:-$BENCH_DATA/runs}${RUN_LABEL:+/$RUN_LABEL}   # BENCH moves the runs root; a label is always its own subdir
# a relative docs patch is relative to where the command runs: made absolute once, before any script changes directory
[ -n "${DOCS_PATCH:-}" ] && { DOCS_PATCH=${DOCS_PATCH:A}; export DOCS_PATCH; }
[ -n "${DOCS_PATCH:-}" ] && [ ! -f $DOCS_PATCH ] && { echo "no docs patch at $DOCS_PATCH" >&2; exit 2; }
# the docs patch's id (the first 16 hex of its sha256; empty without a patch): stand.json and the base record it
patch_id() { [ -n "${DOCS_PATCH:-}" ] && python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" $DOCS_PATCH; return 0; }
# a case of a run continues only with the key and the docs patch it began with (its stand.json): its earlier sessions
# were briefed on those docs and judged against that key. same_run <the case's results dir>
same_run() {
  [ -f $1/stand.json ] || return 0
  local had=(${(f)"$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('key') or 'documented');print(d.get('docs_patch') or '-')" $1/stand.json)"})
  local pid=$(patch_id)
  [ "${had[1]}" = "${KEY:-documented}" ] || { echo "${1:t} was run with KEY=${had[1]}, not ${KEY:-documented}: continue it with the same KEY, or use another RUN_LABEL" >&2; return 1; }
  [ "${had[2]}" = "${pid:--}" ] || { echo "${1:t} was run with the docs patch '${had[2]}', not '${pid:--}' ('-' = none): continue it with the same docs patch, or use another RUN_LABEL" >&2; return 1; }
}
CASES=$WORKSPACE/cases; TASKS=$WORKSPACE/tasks${RUN_LABEL:+/$RUN_LABEL}   # a run's key is frozen with its label
RESULTS=${RESULTS:-$WORKSPACE/results${RUN_LABEL:+/$RUN_LABEL}}; [[ $RESULTS = /* ]] || RESULTS=$WORKSPACE/$RESULTS
for _v in HOST_REPO BENCH_DATA B RESULTS; do _spaced $_v "${(P)_v}"; done
PLUGINS=$BENCH_DATA/plugins
ARMS=${ARMS:-BARE}; ARM_LIST=(${(s:,:)ARMS})
RUNS=${RUNS:-2}; PAR=${PAR:-3}
export STAND WORKSPACE CASES TASKS HOST_REPO BENCH_DATA B RESULTS PLUGINS ARMS RUNS PAR
export BRIEF_MODEL JUDGE_MODEL

arm_family() { print -r -- ${1%%-*}; }
arm_families() {   # the families of the arms given, each once, in order
  local a f; local -a out
  for a in $@; do f=$(arm_family $a); (( ${out[(Ie)$f]} )) || out+=($f); done
  print -r -- ${out[*]}
}
has_hook() { (( $+functions[$1_$2] )); }   # has_hook arm_prep TRAIL
arm_runs() { local f=$(arm_family $1); has_hook arm_runs $f && arm_runs_$f $1 || print -r -- $RUNS; }
# a copy of a directory tree that shares blocks with the source where the file system can (APFS clone, reflink)
clone_tree() { if [[ $OSTYPE == darwin* ]]; then cp -cR $1 $2; else cp -R --reflink=auto $1 $2; fi; }
# a command's wall time and peak memory into a file: timed <file> <command…> (BSD time -l, GNU time -v; neither: nothing)
timed() {
  local f=$1; shift
  if [[ $OSTYPE == darwin* ]]; then /usr/bin/time -l "$@" 2> $f
  elif /usr/bin/time -v true 2>/dev/null; then /usr/bin/time -v "$@" 2> $f
  else "$@" 2> $f; fi
}
TIME_RE='real|maximum resident|peak memory|Elapsed \(wall|Maximum resident'

for _a in $STAND/arms/*.zsh(N); do source $_a; done
unset _a _l

stand_ready() {   # refuse to run on a stand setup.sh has not built: every family of the arms reports ready
  local f
  command -v claude >/dev/null || { echo "no claude (Claude Code) on PATH" >&2; return 1; }
  for f in $(arm_families $ARM_LIST); do
    [ -f $STAND/arms/$f.zsh ] || { echo "no adapter arms/$f.zsh for the arms in ARMS" >&2; return 1; }
    has_hook arm_ready $f && ! arm_ready_$f && { echo "stand not built for $f: run $STAND/bench.sh setup" >&2; return 1; }
  done
  return 0
}
