# The user's own tool as an arm

An arm is one adapter file, `arms/<FAMILY>.zsh`, plus a paragraph `integration-<FAMILY>.md` appended to each clone's
`CLAUDE.md` (`OWN_TASKS.md` §13 and the header of `arms/BARE.zsh` list every key and hook).

In a plugin install the kit's folder is read-only: put the adapter into the kit folder of a clone of the kit, or ask the
user where their copy of the kit lives. Then:

1. Copy the closest shipped adapter: `SERENA.zsh` for an MCP server, `TRAIL.zsh` or `GRAPHIFY.zsh` for a CLI with an index.
2. Declare `ARM_<F>_TOOL` (the prompt's tool sentence), `ARM_<F>_CLI`, `ARM_<F>_USED`, `ARM_<F>_BLIND`,
   `ARM_<F>_OVERLAY` — single-quoted values.
3. Add only the hooks the tool needs: `arm_setup_<F>` (check the pinned version), `arm_build_<F>` (its index, inside the
   clone, from the snapshot — never from the live repository), `arm_session_<F>` (its MCP server, PATH or allowed tools).
4. Keep its paragraph as plain and as long as the shipped ones: names its verbs and where its index is, nothing about the
   repository's rules.
5. `selftest/selftest.sh --arms BARE,<FAMILY>` — the stand-in checks the tool installs, indexes, is called and scored.
