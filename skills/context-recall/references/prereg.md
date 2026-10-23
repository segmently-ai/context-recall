# Preregistration

Write `<ws>/prereg/<YYYY-MM-DD>.md` with the user before any session runs (`METHODOLOGY.md` §11):

```
Question     <what the user wants to know, one sentence>
Stages       brief | spec | architecture | task (which, and why)
Arms         <ARMS>, reference BARE; models <BRIEF_MODEL> / judge <JUDGE_MODEL>
Cases        tuning: <ids> · held-out: <ids>
Primary      share of rule items provided (per stage)
Secondary    provided or partial; files to change named; cost per session; tool-used rate
Analysis     stats.py --ref BARE --by stage; 95% case bootstrap; a difference whose interval holds 0 is not a finding
Judge        threshold for the cheaper judge: provided-vs-not agreement ≥ <0.8> and kappa ≥ <0.6> on <2> tuning cases
Calibration  <the edit planned, if any>; compared with compare_runs.py on tuning, then once on held-out
```

The user confirms it → `workspace.py phase pilot`. Later changes are added as dated lines, never edited in.
