#!/bin/zsh
# Builds and checks the stand from its config (stand.env), idempotent: run it before a benchmark run and after changing a pin.
#   1 the host repository (HOST_REPO) and the data dir ($BENCH_DATA)
#   2 every arm family of ARMS: its adapter's arm_setup_<F> installs or checks the tool against its pin (arms/<F>.zsh);
#     user-level tools are checked, never upgraded
#   3 Claude Code against CLAUDE_VERSION (another version is a warning, recorded per case)
#   4 $BENCH_DATA/stand.json (stand_manifest.sh)
# Exit 0 ready · 2 a pin is not met (the message says what to do). ALLOW_DRIFT=1 turns a tool version mismatch into a warning.
set -u
H=${0:A:h}; source $H/lib.sh
fail() { echo "setup: $*" >&2; exit 2; }
warn() { echo "setup: warning: $*" >&2; }
check() {   # name, found version line, pin, how to install
  if [[ "$2" != *"$3"* ]]; then
    [ -n "${ALLOW_DRIFT:-}" ] && warn "$1 is '$2', the pin is $3 ($4)" || fail "$1 is '${2:-missing}', the pin is $3 — $4 (or ALLOW_DRIFT=1)"
  else echo "$1 $3"; fi
}
mkdir -p $PLUGINS $BENCH_DATA/tools $B

# 1 the host repository
git -C $HOST_REPO rev-parse --git-dir >/dev/null 2>&1 || fail "HOST_REPO is not a git repository: $HOST_REPO (stand.env)"
echo "host $HOST_REPO · data $BENCH_DATA · arms ${ARM_LIST[*]}"

# 2 the arm families
for F in $(arm_families $ARM_LIST); do
  arm_file $F || fail "no adapter arms/$F.zsh (kit or workspace) for the arms in ARMS"
  has_hook arm_setup $F && arm_setup_$F
done

# 3 Claude Code
CV=$(claude --version 2>/dev/null | head -1)
[ -n "$CV" ] || fail "no claude (Claude Code) on PATH"
[[ "$CV" = *"${CLAUDE_VERSION:-}"* ]] && echo "claude ${CLAUDE_VERSION:-$CV}" || warn "Claude Code is '$CV', the pin is $CLAUDE_VERSION (recorded per case)"

# 4 the manifest
$H/stand_manifest.sh > $BENCH_DATA/stand.json && echo "stand ready: $BENCH_DATA (manifest stand.json)"
