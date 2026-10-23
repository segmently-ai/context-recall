# Configure

Edit `<repo>/.context-recall/stand.env` with the user (each key is commented there):

- `ARMS` — the tools to compare, comma-separated. `BARE` (the agent alone) is the reference; keep it. Add `SERENA`,
  `GRAPHIFY`, `TRAIL` only if `bench.sh setup` passes for them; the user's own tool: `arms.md`.
- `RUNS` (sessions per arm per case, 2 is the default and the minimum for a claim), `PAR` (sessions at once; 3 fit in 16 GB).
- `BRIEF_MODEL`, `JUDGE_MODEL` — Claude Code aliases; the judge is calibrated later (`numbers.md`).
- `REQUEST_FIELD` — `request_en`, or another language field the cases carry.
- `TEST_DIRS`, `DOCS_RE` — what counts as a test file and as reading docs in this repository.
- `BASE_STRIP` — files removed from every snapshot: an in-repo copy of a tool under test, local settings.

Then `BENCH_WORKSPACE=<ws> <kit>/bench.sh setup` (installs or checks the tools against their pins). Pass →
`workspace.py phase candidates`.
