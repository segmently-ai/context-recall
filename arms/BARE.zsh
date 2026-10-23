# The BARE arm: the agent alone, with its own tools (search and read the repository). Nothing is added to its clone.
# An adapter declares (single-quoted values, read by the Python scripts too):
#   ARM_<F>_TOOL     the tool sentence of the prompt: "Explore this change with <TOOL> and write a brief …"
#   ARM_<F>_CLI      a word that marks a Bash call as the tool's (score.py: the cost by source); empty = none
#   ARM_<F>_USED     how score.py decides the session used the tool: always | mcp | cli | cli,skill
#   ARM_<F>_BLIND    words the judge never sees (regex alternatives, case-insensitive); each becomes [tool]
#   ARM_<F>_OVERLAY  what arm_prep adds to the clone (comma-separated paths): score.py's leak audit reads them
#   ARM_<F>_ABOUT    one line for the arm's card (workspace.py arms: the user picks the arms from the cards)
#   ARM_<F>_NEEDS    commands the tool's install needs on PATH (e.g. uv, npm); the card says when one is missing
#   ARM_<F>_BIN      the tool's command on PATH once installed; empty = setup installs it into the data dir
#   ARM_<F>_INSTALL  how to install it ($<KEY> = the pin in stand.env), shown on the card while it is missing
# and may define hooks, all optional: arm_setup_<F> (setup.sh: install or check the tool), arm_ready_<F> (the stand is built),
# arm_manifest_<F> (a JSON object merged into stand.json), arm_prep_<F> <clone> <arm>, arm_build_<F> <clone> <case dir> <log>,
# arm_session_<F> (run.sh: sets SENT, MCP, TOOLS, EXTRA_PATH, PLUGIN, HOW), arm_runs_<F> <arm> (sessions per case),
# arm_post_<F> and arm_collect_<F> (cycle.sh: extra steps after the judge, extra files into the results).
ARM_BARE_TOOL='the tools you have (search and read the repository)'
ARM_BARE_CLI=''
ARM_BARE_USED='always'
ARM_BARE_ABOUT='Claude Code alone: its own search and reading of the repository (the reference, always in)'
ARM_BARE_NEEDS=''
ARM_BARE_BIN=''
ARM_BARE_INSTALL=''
ARM_BARE_BLIND=''
ARM_BARE_OVERLAY=''
