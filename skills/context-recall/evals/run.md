# Running the skill evals

1. Build the fixtures in a scratch folder: `selftest/make_demo_repo.sh <dir>` for the demo; for E3 and E4 also
   `workspace.py init --repo <demo>`, then set the phase (`workspace.py phase batch|pilot`), and for E3 add `"pilot"` to
   `labels` and `["d01","d02"]` to `tuning` in `state.json`; for E4 copy `selftest/cases/*.case.json` into the workspace's
   `cases/`. E1: `git init`, two commits with `feat:` subjects.
2. For each scenario start a fresh agent with: the path of `SKILL.md` (it reads the skill and its references itself), the
   fixture path as the user's repository, the user's message, PATH beginning with `selftest/bin` (the stand-in `claude`), and
   the instruction to act as the skill would — run what the skill says to run, except anything that starts brief sessions,
   judge calls or tracing agents, which it must instead describe as its next action — then report its reply to the user
   word for word and every command it ran.
3. Grade each report against the scenario's expectations; record pass/fail per expectation with the evidence (a quoted line
   or a command). Fix the skill and rerun the failed scenarios until all pass.
