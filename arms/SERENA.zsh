# The SERENA arm: Serena's symbol tools as an MCP server, the only MCP server of the session. A uv tool, checked, never
# installed or upgraded by the stand (SERENA_VERSION).
ARM_SERENA_TOOL="Serena's symbol tools (the \`serena\` MCP server) along with your other tools"
ARM_SERENA_CLI='serena'
ARM_SERENA_USED='mcp'
ARM_SERENA_BLIND='serena'
ARM_SERENA_OVERLAY='CLAUDE.md'
ARM_SERENA_ABOUT='Serena: symbol tools (find symbols and their references) as an MCP server'
ARM_SERENA_NEEDS='uv'
ARM_SERENA_BIN='serena'
ARM_SERENA_INSTALL='uv tool install serena-agent==$SERENA_VERSION'
SERENA_BIN=${SERENA_BIN:-$(command -v serena)}
export SERENA_BIN

arm_setup_SERENA() {
  check serena "$($SERENA_BIN --version 2>/dev/null | head -1)" $SERENA_VERSION "uv tool install serena-agent==$SERENA_VERSION"
}
arm_manifest_SERENA() {
  python3 -c 'import json,sys; print(json.dumps({"tools": {"serena": sys.argv[1]}, "pins": {"serena": sys.argv[2]}}))' \
    "$($SERENA_BIN --version 2>/dev/null | head -1)" "$SERENA_VERSION"
}
arm_prep_SERENA() { cat $STAND/integration-SERENA.md >> $1/CLAUDE.md; }
arm_session_SERENA() {
  cat > $MCP <<JSON
{"mcpServers":{"serena":{"command":"$SERENA_BIN","args":["start-mcp-server","--project","$W",
"--context","claude-code","--agent-interface","tools","--mode","planning","--mode","no-onboarding","--mode","no-memories","--transport","stdio",
"--enable-web-dashboard","false","--open-web-dashboard","false"]}}}
JSON
  TOOLS+=(mcp__serena)
}
