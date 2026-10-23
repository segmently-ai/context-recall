# Arms

`<kit>` is this plugin's folder — `~/.claude/plugins/cache/context-recall/context-recall/<version>/` when installed (two
levels above this skill's base directory), or the user's clone of the kit. `<ws>` is `<repo>/.context-recall`. A run's
label (`RUN_LABEL`) is the name of one set of runs, e.g. `base`: its results stay apart from every other label's.

## Adding a shipped arm later

The user started with fewer arms (often BARE alone) and wants another shipped tool now:

1. `workspace.py arms --repo <repo> --json` — its card says what it takes on this machine; on a yes, run the install shown.
2. `workspace.py arms --repo <repo> --set <every arm wanted besides BARE>`, then `BENCH_WORKSPACE=<ws> <kit>/bench.sh setup`.
3. `selftest.sh --arms BARE,<FAMILY>` (free) — the tool installs, indexes, is called and scored.
4. On the label's cases, one at a time: `BENCH_WORKSPACE=<ws> RUN_LABEL=<label> <kit>/bench.sh case <id> --clean --resume`.
   Only the new arm's sessions run and are judged; the earlier sessions keep their briefs and verdicts. Cost line: the new
   arm's sessions and their judge calls only.

The comparison stays fair: the same snapshots, prompt, key and judge. If the judge model changed since, use a new label
for everything instead.

## The user's own tool as an arm

The common case: the user built something that finds context for an agent — a discovery skill, a rules plugin, an MCP
server, a code-map CLI — and wants to know whether it brings more of the written rules than Claude Code alone. The kit
does not change: the arm lives in the workspace (`<ws>/arms/`), so the plugin install stays read-only and updates keep it.

**Order:** the workspace first (`workspace.py init`, onboarding), then `add-arm`, then `arms --set`, then the free check.

**Ask three questions, one at a time**, with a recommended answer each:

1. **What kind is it?**
   - `plugin` — a Claude Code plugin with a skill (a discovery skill is this kind). The sessions load the plugin from its
     folder (`--plugin-dir`) and are told to use that skill;
   - `mcp` — an MCP server; it is the session's only MCP server;
   - `cli` — a command on PATH, optionally with an index built in each case's copy of the repository.
2. **Where is it?**
   - plugin, installed: its id as `claude plugin list` prints it, `<plugin>@<marketplace>` — `add-arm` finds the current
     install folder itself. Plugin under development: the folder of its checkout (the one with `.claude-plugin/plugin.json`).
     Then the skill: the name of its folder under `<plugin>/skills/` (`ls <folder>/skills`). If the skill runs the plugin's
     own command (`<folder>/bin/<command>`), name it with `--cli`: the sessions get that `bin/` on PATH, and a session that
     runs the command counts as using the tool too;
   - mcp: the server's executable and its arguments (`{repo}` stands for the repository copy the session runs in);
   - cli: the command, and the command that builds its index, if any.
3. **What is it called?** A short name in capitals, e.g. `DISCOVER` — it heads the tables.

**Then one command** writes the adapter `<ws>/arms/<NAME>.zsh` and its paragraph `<ws>/arms/integration-<NAME>.md`:

```
python3 <kit>/skills/context-recall/scripts/workspace.py add-arm --repo <repo> --name DISCOVER --kind plugin \
  --plugin <plugin>@<marketplace> --skill <skill> [--cli <the plugin's command>]
python3 … add-arm --repo <repo> --name DOCS --kind mcp --command <executable> [--arg <a> --arg {repo} …]
python3 … add-arm --repo <repo> --name MAPPER --kind cli --cli <command> [--index "<command that builds the index>"]
```

It refuses a name already taken, a plugin folder without `plugin.json`, a skill the plugin lacks, an MCP command that is not
found (a CLI's command is checked by `bench.sh setup`). `--about "<one line>"` sets the text of the arm's card only. `--replace` rewrites the user's own arm of that
name — after a plugin update (its install folder carries the version), run the same command with `--replace`, and say
that a new version is a new arm: compare it under a new label.

**After it:**

1. Show the paragraph `<ws>/arms/integration-<NAME>.md`: every session of this arm gets it in `CLAUDE.md`. Generated for a
   plugin: "This repository copy has the `<skill>` skill of the `<plugin>` plugin. Use it while you explore a change." It
   may say what the tool does, the way the kit's `<kit>/integration-TRAIL.md` names Trail's verbs — never anything about
   the repository's rules: that would hand the arm the answer.
2. `workspace.py arms --repo <repo> --set <the arms besides BARE>,<NAME>` — the arm shows on the cards as "your own".
3. **Free check:** `<kit>/selftest/selftest.sh --arms BARE,<NAME> --own-arms <ws>/arms`. It proves the wiring, not the
   tool: the arm loads, its prompt names the tool, and a call to the tool is counted as use. The stand-in never runs the
   user's skill. PASS → next step.
4. **The cheapest real look** (cost gate): `<kit>/selftest/selftest.sh --real --cases d01,d02,d03 --arms BARE,<NAME>
   --own-arms <ws>/arms` — 3 cases × 2 arms = 6 real sessions + 6 judge calls on the kit's small demo repository, about
   $1–3 API-equivalent, drawn from the user's plan limits. It shows the real skill running and being used.
5. **The real comparison** follows the phases: candidates, tracing, the preregistration, then the runs. Say the whole
   budget before the first paid step, from the pilot's own numbers once there are any:
   - tracing: one subagent per picked task, roughly $0.5–2 each — 10–20 tasks ≈ $5–40, paid once;
   - runs, BARE plus one own arm: cases × 2 arms × RUNS sessions plus as many judge calls. Estimate a session from the
     repository: about $0.1–0.5 for a small one (under ~50k lines), $0.3–2 for a large one; a judge call $0.05–0.2. E.g. 5
     tuning cases × 2 × 2 = 20 sessions + 20 judge calls ≈ $3–10 small, $7–45 large; the held-out cases cost the same again;
   - after the pilot (one case, `RUNS=1`), replace the estimate with its real cost per session from `summary.md`.

**Reading the result for the user's arm** (`numbers.md`): in a case's `summary.md`, the "tool used" column must say True
for its sessions — a session that never called the tool is reported, not scored as the tool's result. Then
`stats.py --ref BARE` gives, for `<NAME>`, the share of the written rules its briefs provided, the difference from BARE with
a 95% interval (an interval that holds 0 shows no difference), and the cases better, worse and equal.

**Worked example — the user's own discovery skill.** "I built a discovery skill in my plugin `acme-context`, installed from
my marketplace `acme`; does it beat plain Claude Code?"

```
python3 <kit>/skills/context-recall/scripts/workspace.py add-arm --repo ~/src/shop --name DISCOVER --kind plugin \
  --plugin acme-context@acme --skill discover --cli acme
python3 <kit>/skills/context-recall/scripts/workspace.py arms --repo ~/src/shop --set DISCOVER
<kit>/selftest/selftest.sh --arms BARE,DISCOVER --own-arms ~/src/shop/.context-recall/arms
```

The sessions then read "Explore this change with the `discover` skill (the `acme-context` plugin) along with your other
tools"; one counts as using it when it calls the skill or runs `acme`. BARE gets the same request with its own search only.

**Fairness.** The arm's paragraph and tool sentence are the only things its sessions get that the others do not. A plugin
installed for the user is not loaded by any session (they read project settings only): the arm loads its own folder.

**By hand.** The generated adapter is plain zsh; the header of `<kit>/arms/BARE.zsh` and `OWN_TASKS.md` §13 list every key
and hook (`arm_setup_<F>`, `arm_build_<F>`, `arm_session_<F>` …) for a tool the three kinds do not cover.
