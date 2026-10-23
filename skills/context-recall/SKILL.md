---
name: context-recall
description: Measure and calibrate how well code-context tools (docs and rules, code graphs, symbol tools, your own tool) put the needed context in front of a coding agent, on your repository's real past tasks — per development stage (brief, spec, architecture, task) or from an operator's seed. Use when someone wants to benchmark context retrieval, compare context tools on their own history, check whether a doc or rule change helps agents, or set up, continue or read such a benchmark. Needs a git repository with a task history (task files, specs, or pull requests with descriptions).
---

# context-recall

**The kit** is two levels above this skill's base directory (`<base>/../..`): `bench.sh`, `history/*.py`, `stats.py`,
`compare_runs.py`, `selftest/selftest.sh`, the method docs (`METHODOLOGY.md`, `OWN_TASKS.md`, `CASE_AUTHORING.md`), and this
skill's `scripts/workspace.py`. Run every kit script with `BENCH_WORKSPACE=<repo>/.context-recall` (the workspace: config,
cases, tasks, results; git-ignored).

## Rules

- Short replies: where we are, the next step, one question when one is needed. Details on request.
- **Cost gate.** Nothing that draws on the user's plan starts without an explicit yes after a cost line: brief sessions
  (`bench.sh case`, `selftest.sh --real`), judge calls (`calibrate.sh`), tracing subagents. The line names the count and
  "~$N API-equivalent, draws on your plan's limits" (`references/runs.md` has the estimates). A yes covers that batch only.
- Never commit, push or publish. Never edit the user's code or docs; a calibration patch is made from their own edits.
- Long jobs (a case, a batch, a calibration) run in the background, one case at a time; report per case.
- Tuning-case numbers are never presented as general; the held-out cases run last, once.
- A failed session or judge call is an error, never a zero: rerun it before reading the case.

## Step 0 — where are we

1. `python3 <kit>/skills/context-recall/scripts/workspace.py status --repo <repo>`
   - no workspace → first contact: `references/onboarding.md`;
   - a workspace → its phase's reference below; a returning user hears the phase, what is done and the next step.
     `status` also prints what the disk holds (cases, preregistration, results per label): when it contradicts the recorded
     phase, trust the disk, say so in one line, and continue from the last phase the disk proves.
2. The prerequisite, before any other step: `workspace.py detect --repo <repo>`. Exit 3 → say what is missing
   (`references/prerequisites.md`) and stop.

## Phases

Record each phase reached with `workspace.py phase <name> --repo <repo>`.

| Phase | Reference | Done when |
|---|---|---|
| `selftest` | `references/selftest.md` | the self-test passes on this machine |
| `configure` | `references/configure.md` (and `references/arms.md` for the user's own tool) | stand.env holds the host, the arms, the models |
| `candidates` | `references/candidates.md` | 10–20 past tasks picked, split into tuning and held-out |
| `tracing` | `references/tracing.md` | every picked task is a case that `validate_case.py` passes, its key reviewed |
| `prereg` | `references/prereg.md` | `prereg/<date>.md` written and confirmed by the user |
| `pilot` | `references/runs.md` | one case ran every arm, its summary read with the user |
| `batch` | `references/runs.md` | every tuning case ran |
| `judge` | `references/numbers.md` | the cheaper judge passed the preregistered threshold, or the stronger one is used |
| `numbers` | `references/numbers.md` | the user has the per-stage table and knows how to read it |
| `calibration` | `references/calibration.md` | the user's edit is compared on the tuning cases, then on the held-out ones |

## Two paths through the same phases

- **Staged** (a history with specs, plans and tasks — `staged` or `speckit` adapter): one case per stage of a feature —
  `spec`, `architecture`, each `task` — so the user sees where along the way their context is lost.
- **Seeded** (task files with `## Read` and `## Run` sections — `taskfiles` adapter): the operator's named docs and files are
  the seed every arm gets; the measure is what discovery adds to it. Seeded and unseeded variants of one task show what the
  seed is worth.

Pull requests with descriptions (`pulls`) give `brief` cases only.
