# Skill evals: the scenarios

Each scenario is played by a fresh agent that follows `SKILL.md` and its references on a fixture, with the self-test's
stand-in `claude` first on PATH (no model sessions are started even if the skill would). A scenario passes when every
expectation holds.

| # | Fixture | The user says | Expectations |
|---|---|---|---|
| E1 | a git repository with commits only (`feat: …` subjects), no task files, no specs, no pull requests | "Measure how well our context tools work on this repo." | runs `workspace.py detect`; says there is no task history and that commit subjects do not count; names the three sources (task files, a specs folder, pull requests with descriptions); suggests writing task files; creates no workspace; starts nothing else |
| E2 | the demo repository (`selftest/make_demo_repo.sh`), no workspace | "Set up the context benchmark here." | first contact: the two-line explanation and the card (history `taskfiles: 3`, arms, workspace path, the self-test as first step at no cost); asks before `workspace.py init`; runs no session |
| E3 | the demo with a workspace at phase `batch`, label `pilot` recorded, tuning `d01,d02` | "Where are we?" | reads `workspace.py status`; says the phase, what is done (the pilot) and the next step (the remaining tuning cases); does not restart earlier phases; a short reply |
| E4 | the demo with a workspace at phase `pilot` and three valid cases | "Just run everything now." | does not start `bench.sh case`; states the count (cases × arms × runs + judge calls) and a cost range "API-equivalent, draws on your plan's limits"; asks for an explicit yes; proposes the pilot first |
| E5 | the demo repository, no workspace | "Compare Trail and the bare agent on our last tasks." | still checks the prerequisite (`detect`); keeps the phase order (self-test, configure with `ARMS=BARE,TRAIL`, candidates, tracing) — no run before there are cases; skips the long explanation |
