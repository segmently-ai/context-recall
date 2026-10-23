# Case authoring: turn a past task into a benchmark case

This is the prompt an agent follows to turn one past task of your repository into a case file. Fill in the placeholders in
angle brackets and give the whole text below the line to the agent. The method behind it is in `METHODOLOGY.md` (sections 3
to 6). A person reads every case the agent writes.

---

# Brief: turn a real past task into a reference benchmark case

You build ground truth for a benchmark. It measures how well code-context tools (code graphs, symbol tools, code maps, a bare
agent) give an agent the right files, docs and must-know rules **before** it plans a change. It may later also measure
whether a rule check after the plan catches a broken rule.

**Inputs.**

- Repository: `<repo>` (a git repository).
- Task `<task id>`: the original task text is below, between the markers.
- Where to start looking: `<commit range, pull request, branch or hints; may be empty>`.
- Working directory: `<working dir>`. Write your output only there.
- The stage: `<brief | spec | architecture | task>` (brief when the history has no stages). For a staged task, its feature
  `<group>` and the texts the stage received (below, each under its label).
- The operator's seed, when the history has one: `<the docs and files the operator named before the work, or none>`.

    --- task text ---
    <task text>
    --- end ---
    --- stage inputs (staged tasks only) ---
    <label>: <text as the history holds it>
    --- end ---

## Hard rules

- **Read-only on the repository.** Never edit, create or delete a file in it. Never run `git checkout`, `reset`, `stash`,
  `clean`, `switch`, `commit` or `push`. Use `git log`, `git show`, `git diff`, `git grep`, `git blame`, `grep` and reading
  files.
- Write only to `<working dir>`.
- Never print or copy secrets (keys, tokens, passwords) into your output.
- Dates are coarse. The task may have been recorded before or after the work. Find the implementation by evidence: commit
  diffs touching the area, plans, specs, dated sections of docs. Many commits have vague subjects ("update docs", "fix"):
  read the diff, not the subject.

## Per case, find

1. **Implementation commits.** The commits that actually did this task: sha, date, subject, and one line on what each did. If
   the task was never implemented, or only researched or planned, say so. The case is then `reject`, or `weak` if a plan with
   a clear design exists and code followed later.

2. **Snapshot.** The parent of the first implementation commit: the repository state an agent would have explored before
   the work. Check that it is an ancestor of every implementation commit (`git merge-base --is-ancestor`). Check that the
   docs the task needs exist there (`git show <snapshot>:<doc>`).

3. **Ground truth at the snapshot.**
   - `files_edit`: existing files the real change edited, each with its main symbol, from the implementation diff. Skip
     lockfiles and generated files. Test files may be listed; they are scored apart.
   - `files_read`: files the change depended on but did not edit, each with why.
   - `docs_must_read`: the docs that hold what the planner must know, each with why.
   - Optional `areas_modify` and `areas_reference`: the parts of the repository the change edits, or only reads, in the
     repository's own terms (top-level directories, packages, services).
   - `must_know_rules`: the rules written in the docs **at the snapshot** that a correct plan must respect. For each:
     - `rule`: the rule's words;
     - `source`: `doc:line`, or `doc:first-last`, valid at the snapshot. Check it with
       `git show <snapshot>:<doc> | grep -n "<words>"`. Several sources are separated by commas. A source is a Markdown doc
       path relative to the repository root. Cite the line that carries the rule, not only its heading;
     - `why`: why it bears on this task;
     - `evidence` that it mattered: a later fix commit, an incident note, a reverted attempt, a review finding. `null` if
       none.

     Prefer rules a plausible plan would break. A rule first written by the implementation commits, or later, is not a
     must-know rule.
   - `undocumented_rules`: rules the real change had to respect that **no** doc held at the snapshot. For each: `rule`,
     `where_in_code` (the file and symbol where it shows) and `evidence`. These measure code reading, not docs.

4. **Reworked request.** A good reference task, in the voice of the person who asked for it:
   - one coherent change. If the original lists several items, keep the one with the clearest implementation and ground
     truth. List the others in `dropped_items`;
   - self-contained: the symptom or the goal as a user sees it. Replace internal URLs and ids with a description. Keep the
     names of screens and features a user of the product would use;
   - no solution hints. Never name the rule, the doc or the file to change;
   - no process boilerplate: no "research first", no tools or skills to call, no "wait for confirmation";
   - write `request_en` (English). If the team writes tasks in another language, add that version too, as
     `request_<language code>`, faithful to the English.

5. **Correct approach** (2 to 4 sentences), and **wrong approaches** a plausible planner would take. Each wrong approach names
   the rule, or the undocumented constraint, it breaks.

6. **Grading.**
   - `stage1`: what a tool's output must contain to count as complete: the areas, docs, files and rules (short labels with
     `doc:line`).
   - `stage2`: for each wrong approach, the conflict a rule check must flag on a plan that takes it:
     `[{"wrong_approach": "...", "must_flag": "conflict with <doc>:<line>"}]`.

7. **Verdict.**
   - `good`: implemented, traceable, at least one documented must-know rule a plan could break, feasible to explore at the
     snapshot;
   - `weak`: usable with caveats; name each caveat in `verdict_reason`;
   - `reject`: say why in `verdict_reason`.

   Also `area`: one or two words for the part of the product the task is about.

Families and drops are curated by a person after you finish. You may suggest them in `notes`: rules that state one
prescription in several docs (a family), and rules that only describe behaviour, with no never, must, do not, only or
always, and that no wrong approach breaks (a drop).

## Per stage

The method is the same at every stage; what changes is what the stage had to know and where its truth is.

- **brief** — one change request before planning: the points above as written.
- **spec** — the feature's request before its spec. The truth covers the whole feature: the areas and docs all its commits
  touched, the rules the feature as a whole had to respect, the files it changed. The snapshot is the commit before the
  feature's first implementation commit.
- **architecture** — the approved spec as input, before the design. The truth: the contracts and boundary files the design
  fixed, the rules that cross areas. Same snapshot as the spec stage.
- **task** — the spec, the design and one task as inputs, before that task. The truth is the task's own commits (files,
  tests) and the rules its change respected. The snapshot is the commit before the task's first commit.

**Inputs are reworked like the request.** Keep each input's text as the history holds it in `original`, and write `text`
for the arms: remove a file of the change named outright, a must-know rule stated outright, and a pointer to a document
that did not exist at the snapshot; say what you removed in `notes`. A rule the input itself states (the spec already says
"only admins may …") goes into `given_rules`, not `must_know_rules`: the stage did not have to find it.

**The seed.** When the operator named docs or files before the work, keep them in `seed` exactly (`{"text", "paths"}`); never
add to the seed what the change later turned out to need.

**The task's own text in the snapshot.** Look at what the snapshot already holds of this task: its task file, the feature's
spec, plan or task list when they were committed before the stage under test. List each in `strip` (globs relative to the
repository root, for example `tasks/d07.md` or `specs/004-billing`): the bench removes them from the snapshot every arm
works on. Never strip a doc the case's rules or `docs_must_read` cite.

## Output

Write `<working dir>/<task id>.case.json` with exactly these keys:

    id, verdict, verdict_reason, area, snapshot, strip (the task's own text the snapshot holds, if any),
    implementation_commits [{sha, date, subject, what}],
    truth {files_edit [{path, symbol}], files_read [{path, why}], docs_must_read [{doc, why}],
           areas_modify (optional), areas_reference (optional)},
    must_know_rules [{rule, source, why, evidence}],
    undocumented_rules [{rule, where_in_code, evidence}],
    correct_approach,
    wrong_approaches [{approach, breaks}],
    grading {stage1, stage2},
    dropped_items,
    request_en (and request_<language code> if asked),
    notes,
    stage, group (staged tasks), inputs [{label, original, text}] (staged tasks), given_rules [{rule, source, why}] (if any),
    seed {text, paths} (if the history has one)

Be exact. Every sha and every `doc:line` you write must be checked with git. Spend your effort on the cases that look `good`.
Stop early on a clear `reject`, and still write its file with the verdict and the reason.

Then reply with one line per case and nothing else:

    <task id> — <verdict> — <snapshot> — <n> rules — <one-line reason>

---

## A hypothetical example

The content below is invented. It shows the shape of a good rule entry and a good request. It comes from no real repository.

Original task: "Exported CSV files show times in the server's zone. Fix it so people see their own time. Also the export
button is slow, and the column order is odd."

    "request_en": "When I export my orders to CSV, the times in the file are not my local times: an order I placed at 9 in
    the morning shows up as 14:00. I expect the export to show the same times I see on the orders screen.",
    "dropped_items": ["the export button is slow", "the column order"],
    "must_know_rules": [
      {"rule": "Timestamps are stored and sent in UTC; only the client formats them, with the viewer's time zone. Never
       format a timestamp on the server.",
       "source": "docs/time.md:18, src/export/README.md:7",
       "why": "The natural fix is to format the times on the server when the CSV is built, which this rule forbids.",
       "evidence": "a1b2c3d (a later commit) reverted a server-side formatting attempt and moved it to the client"}
    ],
    "wrong_approaches": [
      {"approach": "format the timestamps on the server with the zone from a request header",
       "breaks": "docs/time.md:18 (never format on the server)"}
    ]

The request names the symptom as the user saw it. It does not say "UTC", "the client" or `docs/time.md`. The two other items
of the original task are recorded as dropped. The rule is written in two docs, so it carries both sources in one entry and is
graded once.
