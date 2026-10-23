# Tracing

Each picked candidate becomes `<ws>/cases/<id>-<slug>.case.json` through one subagent that follows `<kit>/CASE_AUTHORING.md`
(the section for the case's stage), read-only on the repository, writing only into the workspace's `cases/`.

1. **Cost gate:** n subagents (at most 3 at once), about $0.5–2 API-equivalent each on a large repository.
2. Give each subagent: the candidate record (JSON from the adapter), the repository path, the workspace's `cases/` dir, the
   case-file keys, the stage, and the request field (`REQUEST_FIELD`). For a seeded candidate, its seed goes into the case's
   `seed`. For a staged candidate, its inputs go into `inputs` (`original` kept, `text` reworked) and a rule the input
   itself states goes into `given_rules`.
3. `BENCH_WORKSPACE=<ws> python3 <kit>/validate_case.py <ws>/cases/*.case.json` — fix every error (send the case back to its
   subagent once); show the warnings to the user.
4. Review with the user the parts a tracer gets wrong most: the snapshot (the commit before the first implementation
   commit), rules that are only descriptions (drop with a reason, or merge into a family), a request that hints at the
   answer, the task's own text left in the snapshot (a "holds the request verbatim" warning: its file goes into `strip`).

All cases valid and reviewed → `workspace.py phase prereg`.
