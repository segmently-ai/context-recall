# First contact

Say, in two lines: this measures how well each code-context tool puts the needed docs, files and written rules in front of
a coding agent before it plans, on past tasks of this repository; and it can calibrate the user's own docs and tools by
comparing runs before and after an edit.

Then run `workspace.py detect --repo <repo> --json` and show one card:

```
Repository   <repo> (<n> commits)
History      <source>: <count> (<glob or dir>) · …        ← or "none: see what is needed"
Arms         BARE always; SERENA / GRAPHIFY / TRAIL when their tools are installed (setup checks them)
Workspace    <repo>/.context-recall (git-ignored)
First step   the self-test: ~2 min, no model calls, no cost
```

Say once, with the card: the workspace is git-ignored, so `git clean -fdx` in the repository deletes it together with every
paid case and result; keep a copy before cleaning.

No history → `prerequisites.md` and stop. Otherwise ask one question: start with the self-test? On yes:
`workspace.py init --repo <repo>`, then `selftest.md`.

If the user arrives with a specific request (e.g. "compare Trail and the bare agent on our last tasks"), skip the card's
explanation, keep the prerequisite check, and go to the phase the request needs, still in order (no runs before cases).
