# Task-history adapters

An adapter lists **candidate tasks** from a repository's task history, as JSON records for the tracer
(`CASE_AUTHORING.md`). It never decides the ground truth: the tracer confirms the implementation commits, the snapshot and
the rules from git.

A task history is a source that holds the task's own text — a task file, a spec, a pull request's description. Commit
subjects alone are not a task history.

## Output

`{"records": [Record…], "skipped": [{"path" | "id", "reason"}]}` (`records.py`). A record:

| Field | Meaning |
|---|---|
| `id`, `source`, `title` | the candidate's id, the adapter, a one-line title |
| `request` | the task's text as the history holds it (the tracer reworks it into the case's request) |
| `seed` | what the operator named before the work started: `{"text", "paths"}` (repo-relative), or null |
| `inputs` | what the stage received from earlier stages (staged histories): `[{"label", "original"}]` |
| `commits` | candidate implementation commits, oldest first (a range to confirm, not truth) |
| `created`, `notes` | when the task text was written; where it came from |

## Adapters

- `taskfiles.py --repo <path> --glob '<glob>' [--glob …] [--json] [--max-commits N]` — Markdown task files with a `## Run`
  section (the task) and an optional `## Read` section (the seed); `--glob` once per folder of task files, and a matched file
  without `## Run` (a plain doc) is not a task file. Every git version whose `## Run` text changed is a candidate; its
  commits are the oldest ones after that version that change a file other than the task files. Untracked task files are
  skipped.
- `pulls.py --repo <path> [--limit N] [--json]` — merged pull requests with a description (GitHub CLI `gh`): the description is
  the task text, the merge commit the candidate implementation; a pull request without a description is skipped.
- `staged.py --dir <features dir> [--json]` — a staged history (`STAGED.md`): one record per stage of each feature (`spec`,
  `architecture`, each `task`), with the earlier stages as inputs.
- `speckit.py --repo <path> --out <features dir>` — writes the staged format from a spec-kit layout (`specs/<NNN-slug>/`
  with `spec.md`, `plan.md`, `tasks.md`); then list it with `staged.py`.
