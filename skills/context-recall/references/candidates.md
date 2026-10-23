# Candidates

List past tasks with the adapter `detect` found (all print JSON with `--json`):

- task files: `python3 <kit>/history/taskfiles.py --repo <repo> --glob '<glob>' [--glob '<glob>' …]` — one `--glob` per
  entry of the `globs` that `detect` found (one per folder of task files)
- staged: `python3 <kit>/history/staged.py --dir <features dir>`; spec-kit: `python3 <kit>/history/speckit.py --repo <repo>
  --out <ws>/history` first, then `staged.py --dir <ws>/history`
- pull requests: `python3 <kit>/history/pulls.py --repo <repo>`

Propose 10–20 by the criteria of `OWN_TASKS.md` §3: implemented and merged, one coherent change, docs that held rules at the
time, a plausible plan that could break one. Prefer recent tasks over old, a mix of areas, and for a staged history whole
features (every stage of one feature). Show the pick as a short table (id, title, stage, commits) and let the user swap.

Split before tracing: about a third **tuning** (used while changing docs or settings), the rest **held-out** (run once, at
the end). Record both lists in `state.json` (`tuning`, `heldout`) and → `workspace.py phase tracing`.
