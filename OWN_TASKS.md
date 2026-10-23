# Run it on your repository and your tasks

This guide takes you from an empty stand to a table you can defend. The method behind each step is in `METHODOLOGY.md`. The
prompt that turns a past task into a case is `CASE_AUTHORING.md`.

Plan for a first study of 10 to 20 cases. Trace and check the cases first. Run sessions only after that.

## 1. What you need

- **A git repository** with:
  - written docs that hold rules (Markdown files: a README per area, design notes, contributor rules);
  - a history of merged changes that you can tie to the tasks they did.
- **Claude Code**, logged in. Note its version: you will pin it.
- **Python 3.9 or newer, zsh and git.**
- **The tools of the arms you run.** Node with npm for TRAIL; uv for GRAPHIFY and SERENA. Your own tool, if you add one.
- **Memory and disk.** Each session, with its tool's server, takes memory. Each case needs a snapshot of the repository plus
  one clone per arm while it runs. Copy-on-write file systems keep the clones small.

Private repositories suit this best. A public repository may be in the model's training data, and then a bare agent already
"knows" it (`METHODOLOGY.md`, section 14, pitfall 13).

## 2. Configure the stand

    cp stand.env.example stand.env

Set at least `HOST_REPO`. The other keys have defaults.

| Key | What to set |
|---|---|
| `HOST_REPO` | The git repository the cases come from. Required. |
| `BENCH_DATA` | A data directory outside the repository: snapshots, arm clones, session output. |
| `ARMS` | Comma list of the arms to run, for example `BARE,SERENA,GRAPHIFY,TRAIL`. The default is `BARE` alone (no install); an arm added later runs on the same cases with `bench.sh case <id> --resume`, which runs and judges only its sessions. |
| `RUNS` | Sessions per arm per case. Default 2. |
| `PAR` | Sessions at once. Default 3. Lower it if memory runs short. |
| `BRIEF_MODEL`, `JUDGE_MODEL` | Claude Code model aliases. One brief model for every arm. |
| `CLAUDE_VERSION` | The pinned Claude Code version. Another version is a warning, recorded per case. |
| `TRAIL_VERSION`, `GRAPHIFY_VERSION`, `SERENA_VERSION` | The tool pins. Setup checks them and never upgrades. |
| `REQUEST_FIELD` | The case field the sessions get as the request. Default `request_en`. |
| `TEST_DIRS` | Comma list of directory names that mark a test file, for example `__tests__,tests,test,spec`. |
| `DOCS_RE` | A regex on a file's path: the reads that count as reading docs in the cost split. Set it to where your docs live. |
| `BASE_STRIP` | Comma globs, relative to the repository root, removed from every snapshot. Use it for files that would favour one arm (an earlier in-repository copy of a tool, local settings). It is also the ablation lever. |
| `LEAK_PROBE_FILES` | Comma list of host files, relative to the repository root, whose long lines must never appear in a session unless the snapshot has them. Pick files that change often, such as the root `CLAUDE.md`. |
| `SUMMARY` | The summary script. Leave the default. |

Any key can be overridden from the environment for one command, for example `JUDGE_MODEL=opus ./bench.sh case <id>`.

## 3. Pick 10 to 20 past tasks

Look at merged pull requests, closed issues and task notes whose implementation is in git. Prefer tasks that:

- changed code, in one coherent change;
- touched an area whose docs held at least one rule (a must, a never, an only) before the change;
- had a trap: a plausible first approach that breaks a rule. A fix commit, a reverted attempt or a review comment is good
  evidence.

Avoid tasks that:

- were only researched or planned, or never landed;
- are operations work, or live in another repository;
- had their rules written by the change itself or after it;
- restate the rule in their own text;
- share an area and the same weeks with another task you picked.

**Check when a rule was written.** For a candidate rule, `git blame <commit> -- <doc>` or `git log -L <a>,<b>:<doc>` shows when
its lines appeared. The rule counts only if it was there at the snapshot (the parent of the first implementation commit).

**Mix the doc ages.** If your docs grew over time, include some older tasks as a stratum (`METHODOLOGY.md`, section 3).

## 4. Trace each task into a case

Give each task to an agent with `CASE_AUTHORING.md` as its prompt. Fill in its placeholders: the task text, the repository
path, a commit range or hints, the case id and a working directory.

- One agent per task, or a few tasks per agent. Run them read-only on the repository: they write only to the working
  directory.
- The agent writes `<working dir>/<id>.case.json` and replies with one line per case.
- Copy the finished files into `cases/`. A case's file name is `cases/<id>.case.json`.

Read every case yourself. The agent's reading of the history is a draft. Check above all:

- the snapshot really is the state before the work;
- each must-know rule is written at the snapshot and a plan could plausibly break it;
- the request gives no hint: it names no rule, no doc and no file.

## 5. Validate

    python3 validate_case.py cases/<id>.case.json

It checks the keys, the verdict, the snapshot and implementation commits, every `doc:line` at the snapshot through git, the
families and the drops. Errors stop the case; fix them and run it again. Warnings ask for your judgement: a dropped rule that
says never, must, do not, only or always may still only describe behaviour, and a request that names a file of the change
gives a hint away. `case2task.py` prints "no quote for …" for a source with no quotable line: cite the line that carries the
rule, not only its heading.

## 6. Curate families and drops

In each case file:

- **Families.** When one prescription is written in several docs, give each of those rules the same `family` value. The key
  then grades it once, and any of its sources counts.
- **Drops.** Add a `drop` reason to a rule only when it describes behaviour (no never, must, do not, only or always) **and**
  no wrong approach of the case breaks it. Never drop a rule because the tools miss it.

Validate again after curating.

## 7. Split held-out and tuning cases, and preregister

- **Tuning cases** (a third is a fair share): pilots, harness checks, judge calibration, any change to a tool, an adapter, the
  prompt or the template.
- **Held-out cases:** run once, with everything frozen. Report these.

Then write the preregistration (`METHODOLOGY.md`, section 11) and date it with a commit or a hash. A minimal version:

    Question: does each arm put the must-know written rules into the brief?
    Primary metric: share of graded items provided (judge: <model>), per arm, over held-out cases.
    Reference arm: BARE. Primary comparison: <ARM> against BARE.
    Arms and pins: <ARMS>, Claude Code <version>, tools <versions>, RUNS=2.
    Cases: held-out <ids>; tuning <ids>; stratum by doc age <ids>; related pairs <ids>.
    Statistics: case bootstrap, 10,000 draws, seed 1, 95% interval; cases better/worse/equal.
    "No difference": the interval includes 0, or the difference is below the MDE estimated on the tuning cases.
    Judge: <model>, accepted if agreement on provided-vs-not >= 0.8 and kappa >= 0.6 against <stronger model>.
    Exclusions: leak flag or path outside -> fix and rerun; judge error -> rerun; tool never called -> kept, reported.
    Published: case files if possible, all results, invalidated runs.

## 8. Build the stand

    ./selftest/selftest.sh   # the whole flow on a synthetic repository with a stand-in claude: no model calls
    ./bench.sh setup         # idempotent: builds and checks the stand from stand.env
    ./bench.sh status        # the manifest, the cases, which have results

Run setup again after you change a pin. Run the self-test first on a new machine, and again after you change the harness or
add an arm (`--arms BARE,MYTOOL`): it shows that every arm's tool installs, indexes, is called and is scored before you
spend anything on your own cases. `./selftest/selftest.sh --real --cases d02` then runs real sessions on one synthetic case,
the cheapest look at each tool at work.

## 9. Run one tuning case end to end

    ./bench.sh case <id>

A case run snapshots the repository at the case's commit, builds the tool-neutral base and one clone per arm, builds each
arm's index, runs `RUNS` isolated sessions per arm, scores every brief, runs the blinded judge and collects everything into
`results/<id>/`.

Then read `results/<id>/summary.md` and a few files in `results/<id>/briefs/`. Check:

- every session wrote a brief, and its tool was really used;
- no leak flag and no path outside;
- no judge error;
- the judge's quoted evidence matches the brief;
- the arms got the same prompt (each session's prompt is saved next to its output).

Fix what you find before you run more cases. A change to the harness, a tool or the prompt is allowed only now, on tuning
cases.

## 10. Run the batch

    ./bench.sh case <id> --clean

- One case at a time. A case already runs `PAR` sessions at once.
- Run it in the background and read its summary when it ends.
- `--clean` deletes the case's clones once the summary is written. The results stay.
- A session or a judge call that failed (for example on a usage limit) is an error, never a zero. Run it again before you
  read the case.
- `./bench.sh summary <id>` rebuilds a case's table; `./bench.sh clean <id>` deletes its clones by hand.

## 11. Calibrate the judge

On the tuning cases, re-judge the saved briefs with a stronger model and compare:

    ./calibrate.sh <id> <stronger model>
    python3 compare_judges.py --tag <stronger model> <ids…>

Accept the cheaper judge only if it meets the threshold you preregistered **and** keeps the order of the arms. If the final
ranking hinges on about half a rule per case, re-judge the arms in question with the stronger model.

## 12. The numbers

    python3 stats.py --ref BARE <held-out ids…>

For each arm it prints: the share of rules provided, and provided or partial, with 95% intervals from resampling cases; the
paired difference against the reference arm, with its interval and the cases better, worse and equal; cost and time; the
tool-used rate.

### How to read them

- **The interval, not the point.** If the paired interval includes 0, you have not shown a difference.
- **Cases better / worse / equal.** A difference carried by one or two cases is fragile.
- **Rules sighted against stated.** A rule sighted but not stated was found and dropped. A rule never sighted was never found.
  They call for different fixes.
- **Files.** Code recall says whether the brief names the right files. Precision says how much else it names.
- **Extras and unsupported claims.** A brief that states many rules may also state many that do not apply, or attribute rules
  to docs that do not say them.
- **Cost.** Compare output tokens and cache reads, not only the total.

### What not to claim

- That a tool is better in general. You measured one repository, one agent, one model, these cases.
- A difference below the minimum detectable effect, except as a direction.
- Results on tuning cases as if they were held-out.
- That a tool failed when it was never called. Report the tool-used rate.
- Any number without the judge model and the pins (`results/<id>/stand.json`).

## 13. Add your own tool as an arm

1. Write `arms/<FAMILY>.zsh`. Start from a shipped adapter close to your tool: SERENA for an MCP server, TRAIL or GRAPHIFY for
   a CLI with an index. The header of the shipped adapters documents every key and hook (`METHODOLOGY.md`, section 7.2).
   Values are single-quoted. A sketch for a hypothetical CLI tool:

       # arms/MYTOOL.zsh (hypothetical)
       ARM_MYTOOL_TOOL='the MyTool index of this repository (the `mytool` CLI) along with your other tools'
       ARM_MYTOOL_CLI='mytool'
       ARM_MYTOOL_USED='cli'
       ARM_MYTOOL_BLIND='mytool|mytool-out'
       ARM_MYTOOL_OVERLAY='CLAUDE.md,mytool-out'
       arm_prep_MYTOOL() { cat $STAND/integration-MYTOOL.md >> $1/CLAUDE.md; }    # <clone> <arm>
       arm_build_MYTOOL() { (cd $1 && mytool index . > $2/mytool-build.out); }   # <clone> <case dir> <log>
       # also: arm_setup_MYTOOL (install or check the pin), arm_manifest_MYTOOL (its version, as JSON),
       # arm_session_MYTOOL (PATH, MCP server or allowed tools the session needs)

2. Write `integration-MYTOOL.md`: one paragraph that names the tool's verbs and where its index is. Nothing about the
   repository's rules or the task. Keep it about as long as the shipped paragraphs.
3. Pin its version in `stand.env` and record it in the manifest.
4. Build its index inside the arm's clone, from the snapshot, never from the host repository.
5. Add the arm to `ARMS` and run one tuning case. Check that the tool was called in every session and that no leak flag
   appears.

## 14. The ablation: the same arms without the docs

Remove the docs from the snapshot and run the same arms into separate directories:

    BASE_STRIP=<the globs stand.env sets>,<your docs globs> BENCH=$BENCH_DATA/runs-ablation RESULTS=results-ablation ./bench.sh case <id>

A value set in the environment replaces the one in `stand.env`, so repeat the globs `stand.env` already sets. Without docs no brief can cite a doc, so compare the
rules stated with any source, and provided or partial, not provided alone (`METHODOLOGY.md`, section 15).

## 15. Cost and time

Per case:

    sessions = arms × RUNS
    cost ≈ sessions × (cost of a brief session + cost of a judge call) + index builds that call a model
    wall time ≈ (sessions / PAR) × (time of a session) + index builds + judge calls / PAR

- Calibration adds one judge call per re-judged brief. Step 2 (the plan and the rule check), if you run it, adds a planner session and a check per brief.
- A session costs more when the agent reads more, so a large repository with long docs costs more per session.
- **Order of magnitude:** with four arms, two runs and a mid-tier model, expect a few dollars to a few tens of dollars
  (API-equivalent) and some tens of minutes per case. On a subscription it draws on usage limits instead. Measure one tuning
  case before you budget the batch.
- Report cache reads and creation apart from fresh input and output. The arm that runs first can look expensive because it
  warms the prompt cache.

## 16. Troubleshooting

- **"stand not built"**: run `./bench.sh setup` and read what it says is missing.
- **A tool version mismatch**: install the pinned version, or change the pin and treat the result as a new benchmark.
- **A trust warning in a session's stderr** (the clone's project permissions are ignored): expected. The workspace is not
  trusted, and that keeps the host's permissions out of the arms.
- **A leak flag**: find which probe matched and how the session reached host text (an absolute path, a tool reading outside
  its clone, an index built from the host). Fix the cause, then run the session again.
- **Disk full**: run cases with `--clean`, and delete the clones of finished cases with `./bench.sh clean <id>`.

## 17. The staged and the seeded paths

**Find your task history** (`history/`):

    python3 history/taskfiles.py --repo <repo> --glob 'tasks/*.md'          # task files: ## Run (the task), ## Read (the seed);
                                                                             # one --glob per folder of task files
    python3 history/speckit.py --repo <repo> --out <dir>                     # specs/<NNN-slug>/{spec,plan,tasks}.md → staged format
    python3 history/staged.py --dir <dir>                                    # one record per stage of each feature
    python3 history/pulls.py --repo <repo>                                   # merged pull requests with a description

Each prints candidate tasks (`--json` for the tracer). They are candidates: the tracer confirms the commits and the
snapshot from git.

- **Staged** (a history that keeps each feature's spec, plan and tasks): trace one case per stage — `spec`, `architecture`,
  each `task` — with `CASE_AUTHORING.md` "Per stage". Give the stages of one feature the same `group`. Read the numbers per
  stage: `python3 stats.py --ref BARE --by stage <ids>`.
- **Seeded** (task files whose `## Read` names what the operator knew): copy the seed into the case. To see what the seed
  is worth, trace an unseeded variant of the same task too and compare: `stats.py --by seeded`.

## 18. Run labels and calibration

Give every run a label: `RUN_LABEL=<label> ./bench.sh case <id> --clean`. A label keeps the run's results
(`results/<label>/`), sessions and task files (`tasks/<label>/`, the key it was graded with) apart, so a later run never
meets or rewrites an earlier one. The kit refuses a case the label already holds; `--resume` continues an interrupted one.

To check whether an edit of your docs helps (`METHODOLOGY.md` §17):

    python3 skills/context-recall/scripts/docs_patch.py make --repo <repo> --out edit.patch   # your doc edits, uncommitted is fine
    KEY=all RUN_LABEL=before ./bench.sh case <id> --clean                                     # for each tuning case
    KEY=all RUN_LABEL=after DOCS_PATCH=edit.patch ./bench.sh case <id> --clean
    python3 compare_runs.py before after

`KEY=all` also grades the rules no doc held at the snapshot; the edit's gain shows as those rules moving to provided.
A case the patch does not fit is left out and listed. When the edit is final, run the held-out cases the same way, once.

The `context-recall` skill (`skills/context-recall/`) walks through all of this in a session: `claude --plugin-dir <kit>`.
