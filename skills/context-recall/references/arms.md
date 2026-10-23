# Adding an arm later

The user started with fewer arms (often BARE alone) and wants another shipped tool now:

1. `workspace.py arms --repo <repo> --json` — its card says what it takes on this machine; on a yes, run the install shown.
2. `workspace.py arms --repo <repo> --set <every arm wanted besides BARE>`, then `BENCH_WORKSPACE=<ws> <kit>/bench.sh setup`.
3. `selftest.sh --arms BARE,<FAMILY>` (free) — the tool installs, indexes, is called and scored.
4. On the label's cases, one at a time: `BENCH_WORKSPACE=<ws> RUN_LABEL=<label> <kit>/bench.sh case <id> --clean --resume`.
   Only the new arm's sessions run and are judged; the earlier sessions keep their briefs and verdicts. Cost line: the new
   arm's sessions and their judge calls only.

The comparison stays fair: the same snapshots, prompt, key and judge. If the judge model changed since, use a new label
for everything instead.

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
