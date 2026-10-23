# context-recall: a benchmark of code-context tools on your own tasks

## What it does

It measures whether a code-context tool puts the rules written in your repository in front of a coding agent before it
plans a change. Your real past tasks become cases; every tool gets the same isolated Claude Code session and prompt, and a
blinded judge grades each brief rule by rule. It also tells you whether an edit to your own docs or tools helped.

## Why it matters

- Without project memory, a coding agent finds about a third of the rules a change has to respect: Claude Code found 32%
  without the project's docs, 54% with them, 70% when the right docs were read whole.
- Almost half of those rules cannot be learned from the code, and most have no test that fails when they are broken: a
  missed rule passes CI.
- Smarter code search adds no rules: Serena, Trail and Graphify found fewer than Claude Code alone.
- Catching a rule while planning costs cents; missing it costs a rework cycle, or an incident in production.

The study behind this kit: [Without Project Memory, Coding Agents Find a Third of the Rules](https://articles.segmently.ai/coding-agents-project-rules).
It was run by the authors of Segmently Modules; that tool's arm is not part of this kit. Run it on your own tasks.

Segmently Modules itself — the project memory that reached 70% in the study — is not part of this kit either. It is a
separate open-source plugin: install it from https://github.com/segmently-ai/segmently-modules-plugins, and add it as an arm
of your own ("Add a tool" below) to measure it next to the others.

## Install with one prompt

Paste this block into a fresh Claude Code session. It checks the tools the kit needs, installs the plugin from this
repository and ends with one message of two steps for you: type `/reload-plugins` (an agent cannot reload its own plugins),
then paste the request it gives you in the repository you want to measure.

```text
Set up the context-recall plugin for Claude Code on this machine, then stop and give me the two next steps.

Marketplace: segmently-ai/context-recall (this GitHub repository is its own marketplace). Plugin: context-recall@context-recall.

Run the steps in order and show me the exact output of every command:
1. git --version, python3 --version, zsh --version and claude --version. git, zsh and Claude Code must answer, and Python must be 3.9 or newer. On macOS, if git or python3 asks for the command line developer tools, run xcode-select --install, ask me to finish the installer it opens, then run all four again. On Linux, if zsh is missing, tell me the package manager command that installs it on this system and stop there. If Python is still missing or older than 3.9, tell me how to get Python 3.9 or newer on this operating system and stop there.
2. node --version and uv --version. These are optional: the kit's setup uses Node with npm for the Trail arm and uv for the Graphify and Serena arms, and runs without them with fewer arms. Only report which are present; install nothing.
3. claude plugin marketplace add segmently-ai/context-recall --scope user
   claude plugin install context-recall@context-recall --scope user
   If the marketplace is already there, run claude plugin marketplace update context-recall and then claude plugin update context-recall@context-recall --scope user.
4. claude plugin list — the output must name context-recall. If it does not, say so plainly and do not continue.
5. Do not use the skill in this session yet. Claude Code picks a newly installed plugin up only after /reload-plugins, which only I can type, or in a new session. Do not try to reload or restart anything yourself, do not start another Claude Code process, and do not run the kit, its self-test or any session that costs money. End with one separate message to me that holds only the text below, word for word:

Setup is done. Two steps for you:
1. Type /reload-plugins in this chat (or start Claude Code in the repository you want to measure).
2. Then, in that repository, paste this request:
"Use the context-recall skill to measure how well code-context tools put the needed docs, files and rules in front of a coding agent in this repository. Start where the skill starts: check that the repository has a task history, then offer the free self-test. Ask me before anything that draws on my plan's limits, with a cost line."
```

The kit never commits, pushes or edits your code or docs. Its workspace lives in `<your repo>/.context-recall/` and is
git-ignored: `git clean -fdx` deletes it, with every case and result.

## As a Claude Code plugin

The kit is also a plugin: its `context-recall` skill leads you through the whole flow in your repository — the self-test, the
configuration, picking past tasks from your history, tracing them into cases with subagents, preregistration, the runs
(each after your yes and a cost line), the numbers per stage, and the calibration of your own docs.

- Install by hand: `claude plugin marketplace add segmently-ai/context-recall`, then
  `claude plugin install context-recall@context-recall`, then `/reload-plugins` or a new session.
- From a clone, without installing: `claude --plugin-dir <path to the clone>`.

Then ask to measure how well your context tools find what an agent needs.

## The method

- `METHODOLOGY.md` — the method as a spec: the question, case selection, tracing, rule families, fairness, scoring, the judge
  and its calibration, statistics, preregistration, pitfalls.
- `OWN_TASKS.md` — step by step: from an empty stand to numbers you can defend, on your repository.
- `CASE_AUTHORING.md` — the prompt an agent follows to turn one past task into a case file.

Each task becomes a case with a known snapshot, the files the change edited and the written rules the change had to respect;
every tool (an "arm") gets the same session, prompt and brief template.

## Quick start

    ./selftest/selftest.sh              # first: the whole flow on a synthetic repository, no model calls, ~2 min
    cp stand.env.example stand.env      # set HOST_REPO; the other keys have defaults
    ./bench.sh setup                    # installs or checks the arms' tools against their pins
    python3 validate_case.py cases/c01-<slug>.case.json
    ./bench.sh case c01 --clean         # one case end to end; results/c01/summary.md
    python3 stats.py --ref BARE c01 c02 …

Requirements: Claude Code (logged in), Python 3.9+, zsh, git; Node with npm for TRAIL; uv for GRAPHIFY and SERENA.

## What a case run does

1. A snapshot of `HOST_REPO` at the case's snapshot commit (no git history), made tool-neutral (`BASE_STRIP`, no project
   plugins or hooks), and one copy-on-write clone per arm with the arm's own additions.
2. The arms' indexes are built (the Graphify graph, the Trail map).
3. `RUNS` isolated headless sessions per arm write a brief: no web, no git, no host settings, no MCP server but the arm's own.
4. Each brief is scored (`score.py`: files, rules seen in the session, cost by source, whether the tool was used, a leak and
   path audit) and judged blind (`judge.sh`, `judge-prompt.md`).
5. `results/<id>/`: the summary, `stand.json` (what the run was made of), every brief with its score and verdict.

## Layout

| Path | What it is |
|---|---|
| `bench.sh` | The entry point: `setup`, `status`, `case <id> [--clean]`, `summary <id>`, `clean <id>` |
| `stand.env` | Your config (from `stand.env.example`): the host repository, the arms, runs, models, pins |
| `arms/<FAMILY>.zsh` | One adapter per tool: the prompt's tool sentence, how to prepare, index and run it, how to score it |
| `integration-<TOOL>.md` | The paragraph an arm's clone gets in its `CLAUDE.md` |
| `cycle.sh`, `prep.sh`, `build.sh`, `run.sh`, `score.py`, `judge.sh` | The steps of one case |
| `case2task.py`, `validate_case.py` | A case file into task files; a case file checked against the repository |
| `summary.py`, `stats.py` | One case's table; the numbers over cases with bootstrap intervals (`--by stage`, `--by seeded`) |
| `history/` | Task-history adapters: task files, the staged format, spec-kit, pull requests (`history/README.md`) |
| `templates/` | The brief templates of the `spec`, `architecture` and `task` stages |
| `compare_runs.py` | Two labelled runs on the same cases — the calibration report |
| `.claude-plugin/`, `skills/context-recall/` | The plugin and its skill, which walks through the whole flow |
| `calibrate.sh`, `compare_judges.py` | The judge's calibration against a stronger model |
| `TEMPLATE.md`, `judge-prompt.md` | The brief template and the judge's prompt |
| `cases/`, `tasks/`, `results/` | Your case files, the task files made from them, the results |
| `selftest/` | The self-test: a synthetic repository with three real tasks, their golden cases, a stand-in `claude`; `--real` runs real sessions on it |

## The self-test

`./selftest/selftest.sh` runs the kit in place (it stays read-only) on a temp folder: it builds a small synthetic
repository (a JavaScript service with five docs of rules, three past tasks and one feature's spec, plan and tasks) and runs
every step on its seven golden cases (four brief cases, one of them seeded, and the spec, architecture and task stages of
one feature): validate, setup, a full case each, stats, judge calibration, a docs-patch calibration. A stand-in `claude`
plays the sessions and the judge, so it costs nothing, while the arms' real tools are installed or checked and their
indexes really built. It passes when every session used its tool, saw every rule and was graded without an error.
`--real` swaps in the real `claude` and skips the calibration steps: 7 cases × 4 arms = 28 sessions and 28 judge calls by
default (about $7 API-equivalent, drawn from your plan's limits); `--real --cases d01,d02,d03` (12 sessions, about $3) is
the cheapest way to see each tool work before you trace your own cases. Your `stand.env`, cases and results are never touched.

## Add a tool

Write `arms/<FAMILY>.zsh` (copy `arms/TRAIL.zsh`: a CLI with an index) or `arms/SERENA.zsh` (an MCP server), add its
`integration-<FAMILY>.md` paragraph, pin its version, and add the family to `ARMS`. `OWN_TASKS.md` section 13 walks through it.
Keep each arm's paragraph as plain as the others: it is the only text an arm gets that the others do not.

## License

The code is MIT (`LICENSE`). The methodology documents — `METHODOLOGY.md`, `CASE_AUTHORING.md`, `OWN_TASKS.md` — are
CC BY 4.0 (`LICENSE-docs`): reuse and adapt them freely, with credit. If you repeat the benchmark or build on the method,
cite this repository.
