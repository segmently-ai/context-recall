# The GRAPHIFY arm: the Graphify code graph of the clone (built in step 2) with its skill and CLI. A uv tool, checked,
# never installed or upgraded by the stand (GRAPHIFY_VERSION).
ARM_GRAPHIFY_TOOL='the Graphify code graph of this repository (the `graphify` skill and CLI) along with your other tools'
ARM_GRAPHIFY_CLI='graphify'
ARM_GRAPHIFY_USED='cli'
ARM_GRAPHIFY_BLIND='graphify|graphify-out'
ARM_GRAPHIFY_OVERLAY='CLAUDE.md,.claude/skills/graphify'
ARM_GRAPHIFY_ABOUT='Graphify: a code graph of the repository, with its skill and CLI'
ARM_GRAPHIFY_NEEDS='uv'
ARM_GRAPHIFY_BIN='graphify'
ARM_GRAPHIFY_INSTALL='uv tool install graphifyy==$GRAPHIFY_VERSION'
GSKILL=${GSKILL:-$(ls $(uv tool dir 2>/dev/null)/graphifyy/lib/python*/site-packages/graphify/skill.md 2>/dev/null | head -1)}
export GSKILL

arm_setup_GRAPHIFY() {
  check graphify "$(graphify --version 2>/dev/null | head -1)" $GRAPHIFY_VERSION "uv tool install graphifyy==$GRAPHIFY_VERSION"
  [ -f "$GSKILL" ] || fail "the Graphify skill file is missing (uv tool graphifyy)"
}
arm_manifest_GRAPHIFY() {
  python3 -c 'import json,sys; print(json.dumps({"tools": {"graphify": sys.argv[1]}, "pins": {"graphify": sys.argv[2]}}))' \
    "$(graphify --version 2>/dev/null | head -1)" "$GRAPHIFY_VERSION"
}
arm_prep_GRAPHIFY() {
  cat $STAND/integration-GRAPHIFY.md >> $1/CLAUDE.md
  mkdir -p $1/.claude/skills/graphify && cp $GSKILL $1/.claude/skills/graphify/SKILL.md
}
arm_build_GRAPHIFY() {   # <clone> <case dir> <log>
  (cd $1 && timed $2/graphify-build.time graphify extract . --code-only --no-cluster > $2/graphify-build.out)
  echo "GRAPHIFY exit=$? $(grep -E "$TIME_RE" $2/graphify-build.time | tr -s ' ' | tr '\n' ' ')" >> $3
}
