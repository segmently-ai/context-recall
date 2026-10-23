# Configure

Edit `<repo>/.context-recall/stand.env` with the user (each key is commented there):

- `ARMS` — set with `workspace.py arms --repo <repo> --set …` (the cards say what each tool takes; BARE, the reference, is
  always kept). An arm whose `bench.sh setup` fails is left out and added later (`arms.md`); the user's own tool: `arms.md`.
- `RUNS` (sessions per arm per case, 2 is the default and the minimum for a claim), `PAR` (sessions at once; 3 fit in 16 GB).
- `BRIEF_MODEL`, `JUDGE_MODEL` — Claude Code aliases; the judge is calibrated later (`numbers.md`).
- `REQUEST_FIELD` — `request_en`, or another language field the cases carry.
- `TEST_DIRS`, `DOCS_RE` — what counts as a test file and as reading docs in this repository.
- `BASE_STRIP` — files removed from every snapshot: an in-repo copy of a tool under test, local settings.

Then `BENCH_WORKSPACE=<ws> <kit>/bench.sh setup` (installs or checks the tools against their pins). Pass →
`workspace.py phase candidates`.
