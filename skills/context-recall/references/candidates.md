# Candidates

List past tasks with the adapter `detect` found (all print JSON with `--json`):

- task files: `python3 <kit>/history/taskfiles.py --repo <repo> --glob '<glob>' [--glob '<glob>' …]` — one `--glob` per
  entry of the `globs` that `detect` found (one per folder of task files)
- staged: `python3 <kit>/history/staged.py --dir <features dir>`; spec-kit: `python3 <kit>/history/speckit.py --repo <repo>
  --out <ws>/history` first, then `staged.py --dir <ws>/history`
- pull requests: `python3 <kit>/history/pulls.py --repo <repo>`

**Screen every candidate before proposing it** — tracing costs subagent sessions, a case that fails these is never worth
them. Mechanical checks first, over the whole list: `git show --stat --format= <commit>` (size, file kinds) and
`git log --oneline <commit>..HEAD --grep "<subject or #number>"` (a later revert or fix). Then read the text. Each failed
check is a `reject`, or `weak` with the reason when the user wants the task anyway.

1. **The text says the goal or the symptom, not only the diff.** "Members can extend a booking" passes; "Refactor
   ReservationService, add extend()" does not: the request would have to be invented from the solution. A description
   written after the work is fine when the goal can be read from it without guessing.
2. **The text is the one from before the work.** A task file: its first committed version
   (`git log --diff-filter=A --format=%h -- <file>`); later edits can carry the answer. An issue: its opening text, not
   the comments that followed the fix.
3. **It landed and stayed.** Merged into the main line, not reverted. A fix within days is evidence of a trap: its commits
   join the implementation.
4. **Its commits can be found.** The pull request's merge or squash commit, or commits that name the task (an id, a PR
   number). Commits of the task mixed into unrelated ones, unnamed → `weak` at best.
5. **One change of hand-written code, or one feature that can be split.** Not docs, config, lockfiles, generated files,
   formatting, a version or dependency bump, a mass rename or a merge of branches only. A large feature is not rejected:
   trace its stages as separate cases (spec, architecture, each task), or, from one large pull request, a `spec`-stage case
   for the feature's goal plus a task case for each clear part with its own files (the rest goes to `dropped_items`).
   Count hand-written files only; past about 30, plan the split before tracing. Reject only a change that mixes unrelated
   tasks no commit boundary separates.
6. **The snapshot is clean.** The parent of the first implementation commit. A long-lived branch merged weeks later: check
   that the docs the task relies on did not change on the main line meanwhile (`git log <first commit>^..<merge>^1 --
   <docs>`); a rule written there after the branch began was not there to find.

Then propose 10–20 by the criteria of `OWN_TASKS.md` §3: implemented and merged, one coherent change, docs that held rules at the
time, a plausible plan that could break one. Prefer recent tasks over old, a mix of areas, and for a staged history whole
features (every stage of one feature). Show the pick as a short table (id, title, stage, commits) and let the user swap.

Split before tracing: about a third **tuning** (used while changing docs or settings), the rest **held-out** (run once, at
the end). Record both lists in `state.json` (`tuning`, `heldout`) and → `workspace.py phase tracing`.
