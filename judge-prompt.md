You grade one discovery brief for a code change. A developer will plan the change from this brief. You decide, rule by
rule, whether the brief puts in front of the planner the repository rules this change must respect. You do not see who or
what wrote the brief. Length is not quality: a long brief earns nothing for its length.

The repository (read-only, at the state the brief was written against) is the current directory. You may read any file in it
to check what a cited doc says. Do not use git.

## The task the brief was written for

{{REQUEST}}

## The must-know rules (the grading key)

{{RULES}}

A rule written in several docs (several sources, or several numbered wordings) is ONE item: the brief provides it when it
carries the rule with any one of those sources. Grade each item once.

## The brief

{{BRIEF}}

## What to return

For each must-know rule, quote the brief's words that carry it (or write "none"), then give one verdict:
- `provided` — the brief states the rule (in any words) and points to a source where the rule is written;
- `partial` — the brief names the topic but not the rule, or states the rule with no usable source;
- `absent` — nothing in the brief carries the rule;
- `wrong` — the brief states the opposite, or advises the approach the rule forbids.

Then list every OTHER rule or constraint the brief states (not the must-know ones). For each, give `applies` (a real rule of
this repository that this task must respect; check the cited doc) or `noise` (does not apply to this task, or the cited doc
does not say it), with a few words why.

Then list unsupported claims: any rule the brief attributes to a doc that does not say it (check the doc).

Reply with ONLY this JSON, no prose before or after:
{"must_know": [{"id": "R1", "evidence": "<quote from the brief or none>", "verdict": "provided|partial|absent|wrong", "why": "<short>"}],
 "extra_rules": [{"rule": "<short>", "source": "<path or none>", "verdict": "applies|noise", "why": "<short>"}],
 "unsupported": [{"claim": "<short>", "source": "<path>", "why": "<short>"}]}
