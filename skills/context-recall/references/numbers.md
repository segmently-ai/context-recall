# The judge and the numbers

**Judge calibration** (cost gate: one judge call per saved brief of the chosen cases):
`BENCH_WORKSPACE=<ws> RUN_LABEL=<label> <kit>/calibrate.sh <id> opus` for two tuning cases, then
`BENCH_WORKSPACE=<ws> RUN_LABEL=<label> python3 <kit>/compare_judges.py --tag opus <ids>`. Accept the cheaper judge only when it meets the preregistered threshold
**and** keeps the order of the arms; otherwise set `JUDGE_MODEL` to the stronger one for the held-out run.
→ `workspace.py phase numbers`.

**The numbers:** `BENCH_WORKSPACE=<ws> RUN_LABEL=<label> python3 <kit>/stats.py --ref BARE --by stage <ids>`. Read them with the user by
`OWN_TASKS.md` "How to read them":

- the interval, not the point: an interval that holds 0 shows no difference;
- cases better / worse / equal: a difference carried by one or two cases is fragile;
- sighted against stated: a rule the session saw but the brief dropped needs another fix than a rule never found;
- per stage: where along spec → architecture → task the rules are lost;
- the tool-used rate before any tool's number.

Never call a tuning-case number general; the held-out run decides.
