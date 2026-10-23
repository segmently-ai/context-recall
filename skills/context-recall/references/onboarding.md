# First contact

Say, in two lines: this measures how well each code-context tool puts the needed docs, files and written rules in front of
a coding agent before it plans, on past tasks of this repository; and it can calibrate the user's own docs and tools by
comparing runs before and after an edit.

Then run `workspace.py detect --repo <repo> --json` and show one card:

```
Repository   <repo> (<n> commits)
History      <source>: <count> (<glob or dir>) · …        ← or "none: see what is needed"
Workspace    <repo>/.context-recall (git-ignored)
First step   the self-test on the arms you pick: ~2 min, no model calls, no cost
```

Say once, with the card: the workspace is git-ignored, so `git clean -fdx` in the repository deletes it together with every
paid case and result; keep a copy before cleaning.

No history → `prerequisites.md` and stop.

**The arms.** Run `workspace.py arms --repo <repo> --json` and ask which tools to compare — one card per arm, with the
question tool when there is one (several may be picked). Each card is the arm's `about` and what it takes on this machine:

- `ready` — nothing to install;
- `install` — "takes an install:" and the `install` line (the user runs it, or `bench.sh setup` does it for Trail);
- `needs` — "needs <missing> (not on this machine) first", then the `install` line.

BARE (Claude Code alone) is always in and is not a choice: say so on its card. Recommend starting with BARE alone — the
first number is how many of the written rules the user's Claude Code finds by itself — and adding a tool later: an arm
added later runs on the same cases without repeating the earlier sessions (`arms.md`).

Then `workspace.py init --repo <repo> --arms <the picked arms, comma-separated, without BARE>` and, after a yes to the
self-test, `selftest.md`. Before the self-test, an arm with `install` or `needs` needs its install done: show the command,
and run it only on the user's yes.

If the user arrives with a specific request (e.g. "compare Trail and the bare agent on our last tasks"), skip the card's
explanation, keep the prerequisite check, and go to the phase the request needs, still in order (no runs before cases).
