# A benchmark of code-context tools on your own tasks

Does a code-context tool put the rules written in your repository in front of a coding agent before it plans a change? This
kit measures it on real past tasks of your repository: each task becomes a case with a known snapshot, the files the change
edited and the written rules the change had to respect. Every tool (an "arm") gets the same isolated Claude Code session, the
same prompt and the same brief template; a blinded judge then grades the brief rule by rule.

- `METHODOLOGY.md` — the method as a spec: the question, case selection, tracing, rule families, fairness, scoring, the judge
  and its calibration, statistics, preregistration, pitfalls.
- `OWN_TASKS.md` — step by step: from an empty stand to numbers you can defend, on your repository.
- `CASE_AUTHORING.md` — the prompt an agent follows to turn one past task into a case file.

## As a Claude Code plugin

The kit is also a plugin: its `context-recall` skill leads you through the whole flow in your repository — the self-test, the
configuration, picking past tasks from your history, tracing them into cases with subagents, preregistration, the runs
(each after your yes and a cost line), the numbers per stage, and the calibration of your own docs. Load it with
`claude --plugin-dir <path to the kit>` and ask to measure how well your context tools find what an agent needs. Its
workspace lives in `<your repo>/.context-recall/` and is git-ignored.

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
