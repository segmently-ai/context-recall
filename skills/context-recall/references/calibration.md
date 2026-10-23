# Calibration: did the edit help?

The user edits their docs (a missing rule written down, a rule moved to where agents look) or a tool's settings. The kit
compares the same cases, arms and key with and without the edit — nothing else may differ.

1. **The patch.** `python3 <kit>/skills/context-recall/scripts/docs_patch.py make --repo <repo> --out <ws>/patches/<name>.patch`
   — the diff of the doc files in the working tree (uncommitted is fine), or `--from <ref> --to <ref>`. Show the user the
   files it touches; a patch that touches a non-doc file is refused (it would change the code under test).
2. **Two runs, the wider key.** Cost gate for both (2 × the tuning batch). Run the tuning cases under label `<name>-a`
   without the patch and `<name>-b` with `DOCS_PATCH=<ws>/patches/<name>.patch`, both with `KEY=all` (the key then also
   grades the rules that were not written at the snapshot — the ones a docs edit is most likely to add):
   `BENCH_WORKSPACE=<ws> RUN_LABEL=<name>-a KEY=all <kit>/bench.sh case <id> --clean`, then
   `BENCH_WORKSPACE=<ws> RUN_LABEL=<name>-b KEY=all DOCS_PATCH=<ws>/patches/<name>.patch <kit>/bench.sh case <id> --clean`.
3. **Compare.** `BENCH_WORKSPACE=<ws> python3 <kit>/compare_runs.py <name>-a <name>-b --out <ws>/results/compare-<name>.md`: per stage and arm
   the change with its interval, and the rules gained and lost by name. A case where the patch did not apply is left out
   and listed.
4. Iterate on the tuning cases only. When the user freezes the edit, run the held-out cases the same way, once, and report
   that comparison as the result.

A tool-setting change uses the same two labels without `DOCS_PATCH` (the setting differs between the runs; the
manifests record it).
