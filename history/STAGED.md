# The staged format

A staged history keeps, per feature, what each stage of the work received and produced, so a case can be traced for every
stage: the spec, the architecture (or plan), each task. Any process that keeps stage records can export to it; the kit
reads it with `staged.py` and writes it from a spec-kit layout with `speckit.py`.

One folder per feature, holding `feature.json`:

```json
{
 "id": "f01",
 "title": "Extend a booking",
 "request": "the feature's request, as it was given",
 "spec": {"text": "the spec as it was approved"},
 "architecture": {"text": "the architecture or plan as it was approved"},
 "tasks": [
  {"id": "T1", "title": "…", "description": "the task as the implementer received it",
   "commits": ["<sha>", "…"], "files": ["<path the task names>", "…"]}
 ],
 "commits": ["<sha of every implementation commit of the feature, oldest first>"]
}
```

- `architecture` may be `null`: the feature then has no architecture stage.
- `commits` and a task's `commits` are candidates for the tracer, not truth: it confirms them and the snapshot of each stage
  (the commit before the stage's first implementation commit).
- The texts are kept verbatim; the tracer reworks what the arms see (`CASE_AUTHORING.md`, stage inputs).

`staged.py --dir <features dir>` lists one record per stage: `<feature>:spec` (the request), `<feature>:architecture`
(the request; the spec as input), `<feature>:<task>` (the request; the spec, the architecture and the task as inputs).
