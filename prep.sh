#!/bin/zsh
# One snapshot per case, one copy-on-write clone per arm, the arm's own additions (its adapter's arm_prep_<F>).
# Usage: prep.sh <tid> <snapshot-commit> [arm ...]     (default arms: ARMS of stand.env; an arm with no adapter is a plain clone)
# The base is tool-neutral for every arm: BASE_STRIP (comma-separated globs, relative to the repository root: earlier in-repo
# copies of a tool, local settings — also the lever of an ablation) is removed, and the snapshot's .claude/settings.json keeps
# no project plugins, hooks, extra marketplaces or extra directories.
set -u
setopt null_glob
H=${0:A:h}; source $H/lib.sh
TID=$1; PARENT=$2; shift 2
ARMS_TO=($@); [ ${#ARMS_TO} -eq 0 ] && ARMS_TO=($ARM_LIST)
BASE=$B/$TID/base

# DOCS_PATCH (a calibration): a diff of doc files only (DOCS_GLOBS, default *.md), applied to the base so every arm and the
# judge read the same patched docs. A patch that does not apply leaves the case out (RESULTS/<tid>/excluded.txt, exit 3).
# A base remembers its patch (.bench-docs-patch): reusing it under another patch, or none, is refused.
PATCH_ID=""
if [ -n "${DOCS_PATCH:-}" ]; then
  [ -f $DOCS_PATCH ] || { echo "no docs patch at $DOCS_PATCH" >&2; exit 2; }
  # a file git cannot read as a patch is the run's error, never a case left out
  # outside any repository: inside one, git apply prefixes the paths with the current subdirectory
  NUMSTAT=$(cd / && git apply --numstat $DOCS_PATCH 2>&1) || { echo "the docs patch $DOCS_PATCH is not a patch git can read: ${NUMSTAT%%$'\n'*}" >&2; exit 2; }
  for p in ${(f)"$(print -r -- $NUMSTAT | cut -f3)"}; do
    ok=0; for g in "${(@s:,:)${DOCS_GLOBS:-*.md}}"; do [[ $p == ${~g} ]] && ok=1; done   # quoted: null_glob would drop *.md
    (( ok )) || { echo "the docs patch touches a non-doc file: $p (DOCS_GLOBS ${DOCS_GLOBS:-*.md})" >&2; exit 2; }
  done
  PATCH_ID=$(patch_id)
fi
if [ -f $BASE/.bench-base-ok ] && [ "$(cat $BASE/.bench-docs-patch 2>/dev/null)" != "$PATCH_ID" ]; then
  echo "the base of $TID was made with another docs patch ('$(cat $BASE/.bench-docs-patch 2>/dev/null)', now '$PATCH_ID'): use another RUN_LABEL, or remove $BASE" >&2
  exit 2
fi
if [ ! -f $BASE/.bench-base-ok ]; then
  [ -e $BASE ] && { echo "$BASE exists without .bench-base-ok — remove it by hand"; exit 1; }
  mkdir -p $BASE
  if ! { git -C $HOST_REPO archive $PARENT | tar -x -C $BASE; } || [ ${pipestatus[1]} -ne 0 ]; then   # never an empty base
    rm -rf -- "${BASE:?}"; echo "git archive of $PARENT failed in $HOST_REPO" >&2; exit 2
  fi
  # then the case's own strip list (its truth): the task's own text the snapshot still holds
  CASE_STRIP=(); [ -f $TASKS/$TID.truth.json ] && CASE_STRIP=(${(f)"$(python3 -c "import json,sys;print('\n'.join(json.load(open(sys.argv[1])).get('strip') or []))" $TASKS/$TID.truth.json)"})
  for g in ${(s:,:)${BASE_STRIP:-}} $CASE_STRIP; do
    [ -n "$g" ] || continue   # an empty entry would match the base itself
    [[ $g == /* || $g == *..* ]] && { echo "strip entry outside the snapshot: $g" >&2; rm -rf -- "${BASE:?}"; exit 2; }
    m=($BASE/${~g}); (( ${#m} )) && rm -rf -- $m
  done
  if [ -n "$PATCH_ID" ]; then
    export GIT_CEILING_DIRECTORIES=${BASE:h}   # git apply on the plain folder, never on a repository above it
    if ! why=$(cd $BASE && git apply --check $DOCS_PATCH 2>&1); then
      mkdir -p $RESULTS/$TID && print -r -- "the docs patch did not apply to $PARENT: ${why%%$'\n'*}" > $RESULTS/$TID/excluded.txt
      rm -rf -- "${BASE:?}"; echo "excluded: $(cat $RESULTS/$TID/excluded.txt)" >&2; exit 3
    fi
    (cd $BASE && git apply $DOCS_PATCH) || { rm -rf -- "${BASE:?}"; exit 2; }
    print -r -- $PATCH_ID > $BASE/.bench-docs-patch
  fi
  [ -f $BASE/.claude/settings.json ] && python3 - $BASE/.claude/settings.json <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
for k in ("enabledPlugins", "hooks", "extraKnownMarketplaces"):
    d.pop(k, None)
d.get("permissions", {}).pop("additionalDirectories", None)
json.dump(d, open(p, "w"), indent=2)
PY
  touch $BASE/.bench-base-ok
fi

for ARM in $ARMS_TO; do
  W=$B/$TID/$ARM; F=$(arm_family $ARM)
  [ -e $W ] && { echo "$W exists — remove it by hand to rebuild"; continue; }
  clone_tree $BASE $W
  has_hook arm_prep $F && arm_prep_$F $W $ARM
  echo "$TID/$ARM ready"
done
