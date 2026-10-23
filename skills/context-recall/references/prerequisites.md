# The prerequisite: a git history and a task history

Both are required. A **task history** holds the task's own text, written before or while the work was done:

- **task files** — Markdown files with a `## Run` section (the task) and optionally `## Read` (the docs and files the
  operator named: the seed), committed to git (`history/taskfiles.py`);
- **a staged history** — a folder per feature with its spec, its architecture or plan, and its tasks: the kit's staged
  format (`history/STAGED.md`) or the spec-kit layout `specs/<NNN-slug>/{spec.md,plan.md,tasks.md}` (`history/speckit.py`);
- **merged pull requests with a description** (GitHub CLI `gh`, `history/pulls.py`).

Commit subjects alone are not a task history: the request would have to be invented, and the benchmark would measure the
invention. Say so plainly, name the three sources, and suggest the cheapest start: writing task files for the next tasks
(a `## Run` section with the task, a `## Read` section with what the operator already knows), so the history grows.

The repository path must have no whitespace (the kit refuses such paths).
