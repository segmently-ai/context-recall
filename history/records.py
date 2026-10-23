"""A candidate task from a task history: what an adapter lists for the tracer, never ground truth (the tracer finds that)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass
class Record:
    id: str
    source: str                      # the adapter: taskfiles, pulls, staged, speckit, …
    title: str
    request: str                     # the task's own text, as the history holds it
    seed: dict | None = None         # what the operator named: {"text": str, "paths": [repo-relative paths]}
    inputs: list = field(default_factory=list)    # what the stage received: [{"label": str, "original": str}]
    commits: list = field(default_factory=list)   # candidate implementation commits, oldest first
    created: str = ""                # when the task text was written (ISO date)
    notes: str = ""
    stage: str = "brief"             # brief | spec | architecture | task
    group: str = ""                  # the feature a staged record belongs to


def to_json(records, skipped=()) -> str:
    """The adapters' output: {"records": [...], "skipped": [{"path" or "id", "reason"}]}."""
    return json.dumps({"records": [asdict(r) for r in records], "skipped": list(skipped)}, indent=1, ensure_ascii=False)
