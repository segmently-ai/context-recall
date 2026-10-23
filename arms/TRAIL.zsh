# The TRAIL arm: the Trail code map of the clone (built in step 2) and its CLI on PATH. setup installs Trail into the stand's
# data dir from the stand's lockfile (tools/trail/package-lock.json: the exact tree), at TRAIL_VERSION.
ARM_TRAIL_TOOL='the Trail code map (the `trail` CLI) along with your other tools'
ARM_TRAIL_CLI='trail'
ARM_TRAIL_USED='cli'
ARM_TRAIL_BLIND='trail|graft'
ARM_TRAIL_OVERLAY='CLAUDE.md'
ARM_TRAIL_ABOUT='Trail: a code map of the repository, with its CLI'
ARM_TRAIL_NEEDS='npm'
ARM_TRAIL_BIN=''
ARM_TRAIL_INSTALL='bench.sh setup installs it into the data dir from the kit lockfile'
TRAIL_BIN=$BENCH_DATA/tools/trail/node_modules/.bin
export TRAIL_BIN

arm_ready_TRAIL() { [ -x $TRAIL_BIN/trail ]; }
arm_setup_TRAIL() {
  local TD=$BENCH_DATA/tools/trail; local TP=$TD/node_modules/@trailhq/trail-code/package.json
  have_trail() { [ -f $TP ] && cmp -s $STAND/tools/trail/package-lock.json $TD/package-lock.json \
    && python3 -c "import json,sys;sys.exit(json.load(open('$TP'))['version']!='$TRAIL_VERSION')"; }
  if ! have_trail; then
    rm -rf "${TD:?}" && mkdir -p $TD && cp $STAND/tools/trail/package.json $STAND/tools/trail/package-lock.json $TD/
    (cd $TD && npm ci --no-fund --no-audit >/dev/null 2>$TD/npm.log) || fail "npm ci in $TD (see npm.log)"
    have_trail || fail "Trail is not $TRAIL_VERSION after npm ci"
  fi
  echo "trail $TRAIL_VERSION: $TRAIL_BIN/trail"
}
arm_manifest_TRAIL() {
  python3 -c 'import json,sys
try: v = json.load(open(sys.argv[1]))["version"]
except OSError: v = ""
print(json.dumps({"tools": {"trail": v}, "pins": {"trail": sys.argv[2]}}))' \
    $BENCH_DATA/tools/trail/node_modules/@trailhq/trail-code/package.json "$TRAIL_VERSION"
}
arm_prep_TRAIL() { cat $STAND/integration-TRAIL.md >> $1/CLAUDE.md; }
arm_build_TRAIL() {   # <clone> <case dir> <log>
  (cd $1 && DO_NOT_TRACK=1 GRAFT_NO_STATUSLINE=1 timed $2/trail-build.time $TRAIL_BIN/trail build . > $2/trail-build.out)
  echo "TRAIL exit=$? $(grep -E "$TIME_RE" $2/trail-build.time | tr -s ' ' | tr '\n' ' ')" >> $3
}
arm_session_TRAIL() { EXTRA_PATH=$TRAIL_BIN:; }
