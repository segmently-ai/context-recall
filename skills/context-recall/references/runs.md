# Runs: the pilot and the batch

Every run has a label: `RUN_LABEL=<label> BENCH_WORKSPACE=<ws> <kit>/bench.sh case <id> --clean`. A label keeps its results
(`<ws>/results/<label>/`), its sessions and its task files (the key it was graded with) apart; the kit refuses a case the
label already holds unless `--resume` (continue an interrupted case). Record each label in `state.json` (`labels`).
A `--resume` runs and judges only the missing sessions (an interrupted case, or an arm added later); a session kept from
before is judged again only when its verdict holds an error. `FROM=4` judges every session again.

**Cost line.** Sessions = cases × arms × RUNS; plus one judge call per session. Estimates (API-equivalent): a session
$0.1–0.5 on a small repository, $0.3–2 on a large one (an MCP-heavy arm costs more); a judge call $0.05–0.2. Say the
total range and the time (a case of 4 arms × 2 runs takes 10–40 minutes).

**Pilot.** One tuning case, every arm, `RUNS=1`, label `pilot`. Read its `summary.md` with the user: the tool-used column
(a tool never called is reported, not scored), judge errors (rerun), the audit line (a leak or a path outside the clone
invalidates the session), cost per session against the estimate. Fix the configuration before the batch.

**Batch.** The remaining tuning cases under one label (e.g. `base`), one case at a time in the background; after each,
one line: the case, its sessions, errors, cost so far. Never reuse a label for a different configuration.

Done → `workspace.py phase judge`.
