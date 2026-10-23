#!/bin/zsh
# One isolated headless Claude Code session per (task, arm, run): explore with the arm's tool, write brief.md.
# The prompt and the template are the same for every arm; only the tool sentence differs (ARM_<F>_TOOL of the arm's adapter).
# The session: no web, no git, no host settings (--setting-sources project), no MCP server but the arm's own, writes only to
# its out dir. The adapter's arm_session_<F> adds the arm's MCP server, tools, PATH or plugin.
# Usage: run.sh <tid> <arm> <run> <request-file> [prompt-override-file]
set -u
H=${0:A:h}; source $H/lib.sh
TID=$1; ARM=$2; RUN=$3; REQ=$4; OVERRIDE=${5:-}
F=$(arm_family $ARM); _t=ARM_${F}_TOOL
SENT=${(P)_t:-}; [ -n "$SENT" ] || { echo "unknown arm $ARM (no arms/$F.zsh with ARM_${F}_TOOL)"; exit 1; }
W=$B/$TID/${SNAP:-$ARM}
OUT=$B/$TID/out/$ARM-$RUN
[ -e $OUT ] && { echo "$OUT exists"; exit 1; }
# the case's stage (tasks/<tid>.truth.json; none = brief) picks the template and whom the brief is for
STAGE=brief; [ -f $TASKS/$TID.truth.json ] && STAGE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('stage') or 'brief')" $TASKS/$TID.truth.json)
case $STAGE in
  brief) TPL=$H/TEMPLATE.md; FOR="plan it" ;;
  spec) TPL=$H/templates/spec.md; FOR="write its spec" ;;
  architecture) TPL=$H/templates/architecture.md; FOR="design its architecture" ;;
  task) TPL=$H/templates/task.md; FOR="implement this task" ;;
  *) echo "unknown stage $STAGE in $TASKS/$TID.truth.json"; exit 1 ;;
esac
mkdir -p $OUT && cp $TPL $OUT/TEMPLATE.md
MCP=$OUT/mcp.json; echo '{"mcpServers":{}}' > $MCP
EXTRA_PATH=""; PLUGIN=()
TOOLS=(Read Grep Glob Bash Skill Agent Task "Write(/$OUT/**)" "Edit(/$OUT/**)")
HOW="Explore this change with $SENT and write a brief"
has_hook arm_session $F && arm_session_$F
if [ -n "$OVERRIDE" ]; then PROMPT=$(cat $OVERRIDE); else
PROMPT="$(cat $REQ)

$HOW for whoever will $FOR to $OUT/brief.md, using the template in $OUT/TEMPLATE.md. Do not plan the implementation and do not edit anything in the repository. The repository copy has no git history."
fi
print -r -- "$PROMPT" > $OUT/prompt.txt
cd $W
START=$(date +%s)
env PATH="$EXTRA_PATH$PATH" DO_NOT_TRACK=1 GRAFT_NO_STATUSLINE=1 claude -p "$PROMPT" \
  --model ${MODEL:-$BRIEF_MODEL} --output-format stream-json --verbose \
  --setting-sources project --strict-mcp-config --mcp-config $MCP $PLUGIN \
  --permission-mode dontAsk --allowedTools $TOOLS \
  --disallowedTools WebFetch WebSearch "Bash(llm:*)" "Bash(curl:*)" "Bash(git:*)" \
  --add-dir $OUT > $OUT/stream.jsonl 2> $OUT/stderr.txt
echo "$TID $ARM $RUN exit=$? wall=$(( $(date +%s) - START ))s" | tee -a $B/$TID/runs.log
