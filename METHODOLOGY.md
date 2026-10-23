# Method: does a code-context tool put the written rules in front of the agent?

This document specifies the method the stand implements. Follow it to repeat the experiment on your own repository. Read it
to critique the method. `OWN_TASKS.md` is the step-by-step guide; `CASE_AUTHORING.md` is the prompt that turns one past task
into a case.

The method was first used to compare code-context tools against a bare agent on one private repository. The kit ships four
arms: BARE (the agent alone, with its own tools), SERENA (symbol tools over a language server), GRAPHIFY (a code graph) and
TRAIL (a code map). You can add your own tool as an arm (section 7.2).

## 1. The question

**Primary question.** Given a real change request and the repository as it was just before that change was made, does the
tool put in front of the agent, before it plans:

1. the written rules the change must respect;
2. the files to change and the files to read;
3. the docs that hold those rules?

A written rule is a prescription in a repository doc: something that must, must never, or may only be done. A rule a
plausible plan would break matters most.

**Why before planning.** A plan is built from what the agent knows when it starts. A rule that never reached the agent cannot
shape the plan. The method therefore grades what the agent hands to the planner, not the final code.

**Out of scope.** Whether the final code is correct. Token savings for their own sake. Answer quality on public question
sets.

### 1.1 Grading steps

- **Step 1: the brief (the kit runs it).** Each arm explores the snapshot and writes a brief to a fixed six-section template
  (`TEMPLATE.md`: files to change, files to read, rules and constraints, tests, docs to update, risks and open questions). It
  does not plan and does not edit. The brief is graded.
- **Step 2: the plan and the rule check (optional).** A fixed planner (same model, same prompt for every arm, read-only tools
  on the snapshot) turns each brief into a plan. A rule check then runs on the plan. It is graded against the case's
  `grading.stage2`: for each wrong approach the plan takes, the conflict the check must flag. A control plan built from the
  case's `correct_approach` measures false alarms. The case files carry what step 2 needs (`grading.stage2`), so it can be
  added later without tracing the cases again.

### 1.2 Development stages and the seed

The needed context changes as work moves along. A case can be any of four **development stages**:

- `brief` — one change request, before planning (the default; every case above);
- `spec` — a feature's request, before its spec is written: the areas, docs and product rules the spec must respect;
- `architecture` — the approved spec as input, before the design: contracts, boundaries, cross-area rules;
- `task` — the spec, the design and one task as inputs, before that task is implemented: its files, rules and tests.

Each stage has its own brief template (`templates/<stage>.md`, sections 1 and 3 shared with the brief) and its own truth,
traced from the history of that stage (`CASE_AUTHORING.md`). The stages of one feature share a `group`; the numbers are read
per stage (`stats.py --by stage`) to see where along the way the context is lost. A stage's inputs are the history's own
texts, reworked like a request (no file of the change, no rule stated outright); a rule its input already states is moved
to `given_rules` and not graded.

The snapshot must not hold the task's own text. A task file committed before its implementation, or a feature's spec, plan
and task list committed before the stage under test, sit in the snapshot and hand every arm the answer (a spec case would
find its spec already written). A case lists such files in `strip` (globs, relative to the repository root); `prep.sh`
removes them from the case's base after `BASE_STRIP`, so every arm and the judge see the snapshot without them.
`validate_case.py` warns about each file of the snapshot that holds a line of the request or of an input's original
verbatim and that no strip removes.

The **seed** is what an operator names before the work starts ("it is in this service; read these docs"). A seeded case
gives every arm the same seed; a seeded and an unseeded variant of one task show what discovery adds to it
(`stats.py --by seeded`).

## 2. Units

- **Case:** one past task, its snapshot commit and its grading key.
- **Session:** one arm, one run, on one case. It writes one brief.
- **Graded item:** one rule family of the case (section 5). The key is the list of graded items.
- **Statistical unit: the case.** Sessions and items within a case are not independent: they share the task, the docs and
  the traps. Runs are averaged within a case. Intervals resample whole cases (section 10).

## 3. Case selection

**Source.** Real past tasks of the repository whose implementation is in git: merged pull requests, closed issues, task
notes with their commits. A real task carries real traps. An invented task carries the author's idea of the traps.

**Snapshot.** The parent of the first implementation commit. That is the state an agent would have explored before the work
began. The snapshot must be an ancestor of every implementation commit.

**A case is `good` when all of these hold:**

- the task was implemented, and the commits that did it can be found;
- the snapshot can be explored: the code and the docs the task needs exist there;
- at least one rule the change had to respect is written in a doc at the snapshot;
- a plausible plan could break that rule.

**`weak`:** usable with caveats, each named in `verdict_reason`. **`reject`:** never implemented, only researched or
planned, no commit traces to the task, operations-only work, work in another repository, or no documented rule.

**Avoid:**

- tasks whose rules were written by the change itself or after it (they were not there to find);
- tasks whose request already states the rule;
- several tasks from the same area in the same weeks (see "related cases" below).

**Number.** 10 to 20 cases is a practical size for one person. Section 10 explains why a benchmark of this size only detects
large effects.

**A stratum by doc age.** Docs grow over time. Cases whose snapshots come from a period when the docs were thinner form a
stratum. Decide before running whether that stratum is part of the primary analysis. Report it apart as well.

**Related cases.** Two tasks in the same area from the same weeks share docs and traps, so they are not independent. Keep
one of them. Or name the pair in the preregistration and check that the result holds with either one left out.

**The held-out set.** Split the cases before any run:

- **Tuning cases** are for pilots, debugging the harness, calibrating the judge, and any change to a tool, its adapter, its
  integration paragraph, the prompt, the template or the judge prompt.
- **Held-out cases** run once, with everything frozen. Their results are the ones you report.
- If you change anything after you have seen held-out results, those cases become tuning cases. You need fresh held-out
  cases.
- If you develop one of the tools, every case you looked at while developing it is a tuning case for that tool.

## 4. Tracing a case

An agent traces each task under `CASE_AUTHORING.md`. A person checks the result. The rules:

- **Find the implementation by evidence.** Read diffs, not commit subjects. Task dates are often coarse, and the work may lie
  before or after them.
- **Ground truth at the snapshot:**
  - `files_edit`: existing files the real change edited, each with its main symbol. Skip lockfiles and generated files. Test
    files may be listed: the scorer separates them (by `TEST_DIRS`) and counts them as tests named, never as code.
  - `files_read`: files the change depended on but did not edit.
  - `docs_must_read`: the docs that hold what the planner must know, each with why.
  - Optional `areas_modify` and `areas_reference`: the parts of the repository the change edits or only reads, in the
    repository's own terms.
- **Must-know rules.** Each rule is written in a doc **at the snapshot**. Each carries:
  - the rule's words;
  - `source`: `doc:line` (or `doc:first-last`), valid at the snapshot, checked with `git show <snapshot>:<doc>`; several
    sources are separated by commas;
  - `why`: why it bears on this task;
  - `evidence` that it mattered: a later fix commit, an incident note, a reverted first attempt, a review finding. Use `null`
    when there is none.
- **Undocumented rules** are listed apart: rules the real change had to respect that no doc held at the snapshot, each with
  where it shows in the code and the evidence. They are not in the judge's key. They mark the part of the needed knowledge
  that only reading the code (or the history) could give, and so the ceiling of what docs can explain.
- **Wrong approaches.** The approaches a plausible planner would take that break a rule, each naming the rule it breaks.
- **Check everything against git.** Every sha exists; the snapshot is an ancestor of the implementation; every `doc:line`
  points at its rule at the snapshot (`validate_case.py`).

**The quote.** `case2task.py` turns each source into an exact quote from the doc at the snapshot: the longest line of the
cited range that it finds in the doc (at least 40 characters). For a one-line reference to a heading it also reads the
lines below, up to the next heading, outside code blocks. The quote is what the scorer looks for in the session (section 8).
A source with no quotable line is reported as "no quote for …" and its rule is not graded. Cite the line that carries the
rule, not only its heading.

## 5. Rule families and drops

**Family.** When one prescription is written in several docs, it is one graded item with every source.

- Mark it by giving each member rule the same `family` value.
- A brief provides the family when it carries the rule with any one of its sources.
- The judge grades a family once.
- When old verdicts are restated under families, a family takes the best verdict of its members.
- Do not merge two different prescriptions because they share a doc or a topic.

**Drop.** A rule leaves the key only when both hold:

1. it describes behaviour: it has no never, must, do not, only or always (or the same force in other words);
2. no wrong approach of the case breaks it.

Each drop names its reason in the rule's `drop` key. A dropped rule stays in the case file and out of the key.

- Never drop a rule because the tools miss it.
- Fix the families and drops of a held-out case before any of its sessions run.

## 6. The request

The request is the task text the agent receives. Rework the original task into a neutral request:

- **One coherent change.** If the original lists several items, keep the one with the clearest implementation and ground
  truth. Record the others in `dropped_items`.
- **The symptom or the goal as a user sees it.** Replace internal URLs and ids with a description. Keep the names of screens
  and features a user of the product would use.
- **No hints.** Never name the rule, the doc or the file to change. No proposed solution.
- **No process boilerplate:** no "research first", no tools or skills to call, no "wait for my confirmation".

The case file holds `request_en` and may hold another language. `REQUEST_FIELD` names the field the sessions get. Use one
language for every case of a study.

## 7. The session and fairness

### 7.1 What every arm gets

- **The same snapshot.** `git archive` of the snapshot commit, so no git history. Then the tool-neutral base:
  - `BASE_STRIP` removes files that would favour an arm, for example an earlier in-repository version of one of the tools,
    or local settings files;
  - project plugins, hooks, extra marketplaces and extra directories are removed from `.claude/settings.json`.
- **One copy-on-write clone per arm**, with that arm's overlay only.
- **The same prompt.** The request, then one sentence: "Explore this change with `<tool sentence>` and write a brief for
  whoever will plan it to `<out>/brief.md`, using the template in `<out>/TEMPLATE.md`. Do not plan the implementation and do
  not edit anything in the repository. The repository copy has no git history." Only the tool sentence differs.
- **The same template, model (`BRIEF_MODEL`), Claude Code version and number of runs (`RUNS`).**
- **Isolation.** Each session is a headless `claude -p` call:
  - project settings only: no user settings and no user memory;
  - only the arm's MCP server (a strict MCP configuration);
  - reading, searching, Bash, skills and subagents allowed; writing only to its own output directory;
  - no web fetch, no web search, no git, no curl;
  - no permission prompts: a call outside the allowed set fails.
- **Order.** Run 1 of every arm starts before run 2 of any arm. `PAR` sessions run at once.

### 7.2 Arms are adapters

An arm is one file, `arms/<FAMILY>.zsh`. Its values are single-quoted, because the Python scripts read them too. It declares:

- `ARM_<F>_TOOL`: the tool sentence of the prompt;
- `ARM_<F>_CLI`: a word that marks a Bash call as the tool's, in the cost split (empty for none);
- `ARM_<F>_USED`: how the scorer decides the session really used the tool: `always`, `mcp` (any MCP call), `cli` (a Bash
  call running the CLI word) or `cli,skill` (that, or a skill call);
- `ARM_<F>_BLIND`: words the judge never sees (regex alternatives, case-insensitive);
- `ARM_<F>_OVERLAY`: the paths the arm adds to its clone (comma-separated); the leak audit reads them.

Optional hooks:

- `arm_setup_<F>`: install or check the tool at its pin;
- `arm_ready_<F>`: is the stand built for this arm;
- `arm_manifest_<F>`: a JSON object merged into the manifest (the tool's version and pin);
- `arm_prep_<F> <clone> <arm>`: add the overlay to the clone;
- `arm_build_<F> <clone> <case dir> <log>`: build the tool's index inside the clone;
- `arm_session_<F>`: what the session needs (its MCP server, extra allowed tools, PATH, a plugin);
- `arm_runs_<F> <arm>`: sessions per case, when it differs from `RUNS`;
- `arm_post_<F>`, `arm_collect_<F>`: extra steps after the judge, extra files into the results.

The arm's `integration-<TOOL>.md` paragraph is appended to the clone's `CLAUDE.md`. Fairness rules for it:

- it names the tool's verbs and where its index is;
- it says nothing about the repository's rules or the task;
- the paragraphs of the arms have comparable length and form;
- BARE gets none.

### 7.3 Fairness rules

- **No arm-specific prompt.** A prompt that asks one arm for something the judge rewards (for example "quote every rule with
  its doc:line") makes that arm incomparable. Run such a prompt as a separate, named variant, never as the tool's main arm.
- **The tool-used check.** Each session's score records whether the tool was really called (`ARM_<F>_USED`). Report the rate
  per arm. A session in which the tool was offered and never called measures the agent, not the tool. Report results over
  all sessions. As a secondary view, report them over the sessions that used the tool.
- **The leak audit.** `LEAK_PROBE_FILES` names host files (as they are now). Their long lines that occur in no file of the
  snapshot or of any arm's overlay become probes, together with the entry names of the host's Claude Code memory index when
  it has one. A probe found in a session's transcript means the session saw the host's
  current state, not the snapshot. Any absolute path in a session's tool calls outside the stand's data directory, the
  temporary directories and the session's own directory is flagged too. That check allows the whole data directory, so it
  does not catch a session that reads another arm's clone; look for other arms' names in flagged or odd paths. A flagged
  session is excluded, the cause is fixed and the session is run again.
- **Blinding.** The judge never sees the arm's name. The tools' names and each arm's `ARM_<F>_BLIND` words are replaced by
  `[tool]` in the brief it grades.
- **The same model** writes every brief, and one judge model grades every brief of a comparison.

## 8. Scoring

### 8.1 Deterministic (`score.py`, per session)

- **Files.** Paths in the brief are resolved against the clone: an exact path, or a unique suffix.
  - *Code recall (change):* truth code files named in section 1 of the brief, over all truth code files. Truth code is
    `files_edit` without docs and without test files.
  - *Code recall (any):* the same, for a path named anywhere in the brief.
  - *Tests named:* test files of `files_edit` named anywhere in the brief.
  - *Precision (raw):* section-1 files that are truth code or truth tests, over all section-1 files.
  - *Precision (alt):* the same, with the `files_read` files counted as acceptable.
  - *Missing paths:* paths that match no file of the clone, or several. Most are made-up paths.
- **Rules sighted.** A family is sighted when the first 60 normalised characters of any of its sources' quotes occur in any
  tool result of the session or of its subagents. *Doc cited:* the brief names the path of any of the family's source docs.
- **Cost.** Total cost (the API-equivalent figure from the session's result), duration, turns, and the token split: input,
  cache creation, cache reads, output. The cost split by source: the characters of tool results that entered an agent's
  context, per source: the arm's CLI, its MCP server, grep, reading docs (paths matching `DOCS_RE`), reading code, other Bash.
- **Audit.** The tool-used flag, leak probes found, paths outside.

### 8.2 The judge (`judge.sh`, `judge-prompt.md`, per session)

For each graded item, one verdict with the brief's words that carry it:

- **provided:** the brief states the rule, in any words, and points to a source where the rule is written;
- **partial:** the brief names the topic but not the rule, or states the rule with no usable source;
- **absent:** nothing in the brief carries the rule;
- **wrong:** the brief states the opposite, or advises the approach the rule forbids.

Then every other rule the brief states, as **applies** (a real rule of the repository this task must respect) or **noise**.
Then **unsupported claims**: rules the brief attributes to a doc that does not say them.

`partial` covers two different things. For a closer reading, sort the partial verdicts in two classes, by hand or with a
second judge pass (the kit ships no script for it): A, the rule itself is stated and only the source is missing; B, only the
topic, a part or a softened form is there. "Rule stated, any source"
is then provided plus A. This matters most in the ablation (section 15).

### 8.3 Definitions used in the tables

- **Provided:** per session, the number of graded items judged `provided`.
- **Provided or partial:** per session, the number judged `provided` or `partial`.
- **Per case:** for each arm, the mean over its runs. Error verdicts are left out.
- **Rules sighted against stated.** Sighted is retrieval: the rule's text reached the session. Stated is selection: the brief
  carries it. Comparing provided among sighted rules with provided among unsighted rules shows where rules are lost: never
  reached, or reached and dropped.
- **Extras:** applies and noise per brief. **Unsupported claims** per brief.

Choose one primary metric in the preregistration. The usual choice is the share of graded items provided. The others are
secondary.

## 9. The judge and its calibration

**Setup.** The judge is a headless call in the tool-neutral base snapshot. It has read-only tools (Read, Grep, Glob): no
Bash, no web, no MCP. It gets the request, the key (for each family its rule texts, every source as `doc:line`, and why it
applies) and the blinded brief. It may open any cited doc to check what it says. A rule with several sources is one item. A
long brief earns nothing for its length.

**Failures.** A failed call (a usage limit, an error) or a reply without parsable JSON is stored as an error verdict, never as
an all-absent one. Error verdicts are left out of the means and run again before the case is read.

**Calibration protocol.**

1. Before calibrating, write down the reference judge (a stronger model), the subset (every brief of at least two or three
   tuning cases, all arms, so the per-arm shift is visible) and the threshold. For example: agreement on provided against
   not of at least 0.8, and Cohen's kappa of at least 0.6.
2. Re-judge the saved briefs with the reference model under a tag: `calibrate.sh <id> <model>`. No new sessions run.
3. Compare: `compare_judges.py --tag <model> <ids…>`. It prints the 4-way agreement and kappa, the agreement and kappa on
   provided against not, the confusion table, and per arm the provided and provided-or-partial counts under each judge.
4. Accept the cheaper judge only when it meets the threshold **and** keeps the order of the arms. A kinder judge lifts weak
   briefs more than strong ones and so narrows the spread between arms. Read the per-arm shift, not only the agreement.
5. When a ranking hinges on about half a rule per case, re-judge those arms with the stronger judge and report that verdict.
6. Optionally grade a few briefs by hand, to anchor both judges.

Cohen's kappa is (p_o − p_e) / (1 − p_e). p_o is the observed agreement; p_e is the agreement expected from each judge's
own shares of each verdict.

## 10. Statistics

**Per case.** For each arm: the mean over runs of provided, and of provided or partial.

**Per arm, over cases.** The sum of the per-case means over the sum of graded items. This pools the cases, so a case with more
items weighs more. Show the per-case table next to it.

**Intervals.** A case bootstrap: draw as many cases as there are, with replacement, 10,000 times, with a fixed seed. For each
draw, recompute the statistic from the drawn cases with all their items and sessions. The 2.5th and 97.5th percentiles give a
95% interval. Items and sessions are never resampled alone.

**Paired differences.** Against a reference arm (`stats.py --ref <ARM>`): per case, the arm's mean minus the reference's mean;
the mean of those differences over cases; its bootstrap interval; and the number of cases better, worse and equal. Pairing
removes case difficulty, which varies a lot between cases.

**Cost and time.** Mean per session, per arm. Cost per provided item. The tool-used rate.

**What a small benchmark can detect.** The minimum detectable effect of a paired comparison is about

    MDE ≈ (z(1 − α/2) + z(power)) × s_d / √n

where `s_d` is the standard deviation, across cases, of the per-case paired difference, and `n` is the number of cases. For a
two-sided α of 0.05 and 80% power, the factor is about 2.8.

- **Cases matter more than runs.** The variance of a case mean is σ²_case + σ²_run / r for r runs. More runs only shrink the
  second term. More cases shrink both.
- **Items per case matter.** A case with k items moves in steps of 1/k. Cases with few items make `s_d` large.
- **Binary per-case outcomes need more cases.** "All rules provided" has a larger `s_d` than a share.
- **A hypothetical example (invented numbers).** If `s_d` is 0.30 of a case's items, 12 cases detect about
  2.8 × 0.30 / √12 ≈ 0.24, a 24-point difference. 40 cases would detect about 13 points.
- Estimate `s_d` on the tuning cases. Fix the number of held-out cases before the held-out run. Report differences below the
  MDE as a direction only.
- With several arms against one reference, there are several comparisons. Name the primary comparison in the
  preregistration. Treat the others as secondary.

**Minimum.** 10 cases and 2 runs per arm. Fewer cases give intervals too wide to separate tools.

## 11. Preregistration

Before the first held-out run, write down the following and date it (a commit or a hash):

- the question and the primary metric;
- the arms, with the tool pins, the model aliases, the Claude Code version and `RUNS`;
- the cases: tuning or held-out, the strata, the related pairs;
- the key: families and drops final;
- the reference arm and the comparisons, primary first;
- the statistics: bootstrap draws, seed, interval;
- the judge model, the calibration threshold, and what you do if the threshold is missed;
- the exclusion rules: leak flags, paths outside, error verdicts, a tool never called; whether each leads to a rerun or an
  exclusion, and how it is reported;
- what result counts as "no difference" (for example, an interval that includes 0, or a difference below the MDE);
- what you will publish, including invalidated runs.

Report every deviation from it as a deviation.

## 12. Cost and hardware

- **Sessions at once (`PAR`).** Each headless session, with its tool's server (an MCP server, a language server), takes
  memory. Start with a low `PAR` and watch memory. Index builds run one at a time.
- **Disk per case.** One snapshot, one clone per arm, the indexes and the session streams. Copy-on-write clones share blocks
  with the snapshot. Without copy-on-write, each clone is a full copy. `--clean` deletes a case's clones once its summary is
  written. The results stay.
- **Cost drivers.** Cases × arms × `RUNS` brief sessions, plus the same number of judge calls, plus index builds that call a
  model, plus calibration re-judges, plus step 2 (the plan and the rule check) if you run it. A session's cost grows with how much the agent reads.
- **Report honestly.** The cost of a session is the API-equivalent figure in its result event. On a subscription it draws on
  usage limits instead. Report cache reads and cache creation apart from fresh input and output. A warm prompt cache makes
  later sessions cheaper, so the arm that runs first can look expensive. Interleave the arms and show output tokens beside the
  cost.

## 13. Reproducibility

- **Pins.** `stand.env` pins the tools, the models and the Claude Code version. `./bench.sh setup` checks the tools and never
  upgrades them. Another Claude Code version is a warning, recorded per case.
- **Manifests.** Every case writes `results/<id>/stand.json`: the pins, the versions found and the harness revision. Compare
  the manifests before you compare results. Results made under different pins form a different benchmark.
- **Snapshots must stay reachable.** Put a tag on each snapshot commit, so a later clean-up of branches cannot remove it.
- **Keep the briefs.** Re-judging, calibration and new metrics need no new sessions.
- **The results directory is self-sufficient.** `summary.py <id>` rebuilds a case's table from `results/<id>/` alone.

## 14. Pitfalls

1. **The judge may not notice text after the template's sections.** A list of rules appended after section 6 reads as an
   addendum, and the judge rarely quotes from it. Keep everything an arm adds inside the six sections. To grade an appended
   list, grade it on its own.
2. **Two looks give a rule two chances.** If you grade "brief plus something" and keep the best verdict of the two, compare it
   with a control: the best of two gradings of the same brief alone.
3. **A cheaper judge narrows the spread between arms.** See section 9, step 4.
4. **Index contamination.** An index built from the host repository, or after the snapshot, must never reach a session. Build
   every index inside the arm's clone, from the snapshot. The leak audit catches host text. It does not catch an index built
   from a later commit, so check each arm's build inputs.
5. **The judge must read the tree the session read.** If an arm writes files into its clone (an index, a generated doc) and
   the brief cites them, the judge, which reads the base snapshot, finds other text there. That inflates unsupported claims.
6. **A rule written only in the root agent-instructions file belongs to no tool's area.** Every session loads `CLAUDE.md` at
   start, so every arm tends to provide such a rule, and it separates no tools. Keep it in the key, but report it apart, or
   prefer rules written in the docs of the areas the change touches.
7. **Tuning on the reported cases.** Section 3.
8. **A tool that was available but never called.** Some agents load MCP tool schemas on demand and then rarely call them.
   Check the tool-used rate before you read a tool's numbers.
9. **Measure the whole session.** A tool that serves fewer files does not make the brief name fewer: the agent makes up the
   difference with its own search. Grade the brief, not the tool's raw output.
10. **Loose matching gives false credit.** Match a cited doc by its full path. A bare file name such as `README.md` matches
    every doc of that name, and a wide line window matches neighbouring rules.
11. **A failed call is not a zero.** A session or a judge call that hit a usage limit must be an error and run again, never an
    all-absent verdict.
12. **Nothing may write into a clone while its sessions run.** A background process of a tool breaks the read-only contract.
    Sessions may react by killing processes, and a broad kill pattern can hit the other sessions running at the same time.
13. **Public repositories may be in the model's training data.** A bare agent may then "know" the repository, which hides the
    effect of any tool. A private repository, or one newer than the model, avoids this.
14. **Old snapshots and new tool formats.** An older snapshot may hold an older format of a tool's own configuration. A shim
    for one arm must change nothing on a current snapshot, and it is recorded in the case's results.

## 15. Ablation: the same arms without the docs

To see how much of an arm's result comes from the docs, remove the docs from the snapshot and run the same arms into separate
directories:

    BASE_STRIP=<the globs stand.env sets>,<your docs globs> BENCH=$BENCH_DATA/runs-ablation RESULTS=results-ablation ./bench.sh case <id>

- A value set in the environment replaces the one in `stand.env`, so repeat the globs `stand.env` already sets.
- Without the docs, no brief can cite a doc, so `provided` is out of reach. Compare "rule stated, any source" (provided plus
  partial A, section 8.2) and provided or partial.
- A rule whose words also sit in a doc you kept (a README, a changelog) still reaches the sessions. Check the key's quotes
  against the docs that remain.
- The undocumented rules (section 4) are the comparison point. They show what code reading alone finds when no doc helps.

## 16. Limits

- The findings hold for the harness they ran in. Another agent may mount tools differently (all at start, or on demand), and
  its results may differ.
- One judge model, even calibrated, is one reader. A planner may use the brief differently. Step 2 (the plan and the rule check) tests that.
- A case's key is one person's (or one agent's) reading of the history, checked by a person. Publish the case files when you
  can, so others can contest the key.

## 17. Calibration: did an edit of the docs help?

A team that changes its own docs or tool settings wants to know whether agents now get more of the rules. The comparison
is valid only when nothing else changes: the same cases, arms, models, key and harness, with and without the edit.

- **The edit as a patch.** The doc edits are taken as one diff of doc files (from the working tree or between two refs) and
  applied to every case's snapshot before the clones are made (`DOCS_PATCH`), so every arm and the judge read the patched
  docs. A patch that touches code is refused: it would change what is measured. Replacing the docs by a later version is
  rejected too: later docs carry everything written since, including docs a case's own change wrote, which can hold the
  answer.
- **A case the patch does not fit is left out.** If the patch does not apply to a snapshot, that case is excluded from both
  sides of the comparison, and the exclusion is reported.
- **The wider key.** A docs edit often writes down a rule that was nowhere at the snapshot. With `KEY=all` the key also grades
  the case's undocumented rules: without the edit a brief can state one but cite no source (at best `partial`); with it, it
  can be `provided`. Both runs of a comparison must use the same key.
- **Labels.** Each run has its own label: its results, its sessions and its key are kept apart, so a later run never meets
  an earlier one's output.
- **Reading it.** `compare_runs.py` gives, per stage and arm, the change in the share provided with its case-bootstrap
  interval and the rules gained and lost by name. Iterate on the tuning cases; when the edit is frozen, run the held-out
  cases once and report that comparison.
