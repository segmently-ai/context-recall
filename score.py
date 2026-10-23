"""Bench iteration 1 — deterministic scoring of one (task, arm, run): files, paths, rule sighting, cost by source, audit.

Usage: score.py <tid> <arm-run> [...]      e.g. score.py c01 BARE-1 TRAIL-1
Reads <bench>/<tid>/out/<arm-run>/{stream.jsonl,brief.md}, the session's subagent transcripts, and tasks/<tid>.truth.json.
Writes <out>/score.json and prints one summary block per run.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import stand  # noqa: E402
BENCH = stand.B
PROJECTS = Path.home() / ".claude/projects"
HOST = str(stand.HOST)
META = stand.arms_meta()   # {family: {cli, used, blind, overlay}} from arms/<FAMILY>.zsh
_CLI = sorted({w for m in META.values() for w in (m.get("cli") or "").split("|") if w})
CLI_RE = re.compile(r"\b(" + "|".join(map(re.escape, _CLI)) + r")\b") if _CLI else None
# which reads count as reading docs in the cost split (DOCS_RE: a regex on the file's absolute path)
DOCS_RE = re.compile(stand.cfg("DOCS_RE", r"(^|/)(CLAUDE|AGENTS|README)\.md$|/docs/.*\.md$"))
# where an arm's session may legitimately read or run things outside its own clone: the stand's data (runs, plugins, tools)
# and the runs root (BENCH may move it anywhere: a clone and its out/ live there), each as given and resolved (macOS's /var
# is a symlink to /private/var: a session may report either)
ALLOWED_PREFIXES = tuple(dict.fromkeys(str(p) for root in (stand.BENCH_DATA, stand.B) for p in (root, root.resolve())))
PATH_RE = re.compile(r"`((?:[\w.@-]+/)+[\w.@-]+\.\w+)(?::\d+(?:[-–]\d+)?)?`")
NORM = re.compile(r"\s+")


def norm(s):
    return NORM.sub(" ", s.replace("`", "").replace("*", "")).strip().lower()


def text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    return str(c)


def events(path):
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass


def tool_log(evs):
    """(tool name, input, result text) per tool call, from transcript or stream events."""
    uses, out = {}, []
    for e in evs:
        msg = e.get("message") or {}
        if not isinstance(msg, dict):   # a system event (e.g. permission_denied) carries a plain-text message
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                uses[b["id"]] = (b.get("name"), b.get("input") or {})
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                name, inp = uses[b["tool_use_id"]]
                out.append((name, inp, text_of(b.get("content"))))
    return out


def source_of(name, inp):
    if name == "Bash":
        cmd = inp.get("command", "")
        m = CLI_RE.search(cmd) if CLI_RE else None
        if m:
            return f"cli:{m.group(1)}"
        if re.search(r"\b(grep|rg)\b", cmd):
            return "bash:grep"
        if re.search(r"\b(cat|sed|head|tail|awk)\b", cmd):
            return "bash:read"
        return "bash:other"
    if name == "Read":
        p = inp.get("file_path", "")
        return "read:docs" if DOCS_RE.search(p) else "read:code"
    if name.startswith("mcp__"):
        return "mcp:" + name.split("__")[1]
    return name


_MARKERS = {}
SKIP_SCAN = {"node_modules", "graphify-out", ".git", "graft", "out"}
# what prep.sh adds to an arm's clone of the base (the adapters' ARM_<F>_OVERLAY); the rest of the clone is the base itself
OVERLAY = tuple(sorted({o for m in META.values() for o in (m.get("overlay") or "").split(",") if o}))


def _files(root):
    if os.path.isfile(root):
        yield root
        return
    for d, sub, files in os.walk(root):
        sub[:] = [s for s in sub if s not in SKIP_SCAN]
        for f in files:
            yield os.path.join(d, f)


def _present(roots, probes):
    """The probes that occur in some file under roots. One read per file; a probe found once is not searched for again."""
    left, found = {p.encode(): p for p in probes}, set()
    for root in roots:
        for f in _files(root):
            if not left:
                return found
            try:
                data = Path(f).read_bytes()
            except OSError:
                continue
            for pb in [pb for pb in left if pb in data]:
                found.add(left.pop(pb))
    return found


def markers(tid):
    """Strings of the host's live files that occur in no file of the snapshot: a session that shows one saw the host, not its
    clone. The probes: the long lines of LEAK_PROBE_FILES (comma-separated, relative to HOST_REPO; default CLAUDE.md) and the
    entry names of the host's Claude Code memory index, when it has one."""
    if tid not in _MARKERS:
        base = BENCH / tid / "base"
        cand = []
        for f in (x for x in stand.cfg("LEAK_PROBE_FILES", "CLAUDE.md").split(",") if x):
            fp = Path(HOST, f)
            if fp.is_file():
                cand += [l.strip() for l in fp.read_text().splitlines() if len(l.strip()) > 60][:200]
        mem = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", HOST) / "memory" / "MEMORY.md"
        if mem.is_file():
            cand += re.findall(r"\[((?:project|feedback|reference)_[a-z0-9_]+)\.md\]", mem.read_text())[:60]
        probes = sorted({c[:70] for c in cand if c[:70].strip()})
        (BENCH / tid / "leak-probes.txt").write_text("\n".join(probes) + "\n")
        # an arm adds its own integration text (CLAUDE.md, the overlay): a marker present in any arm's snapshot is no leak.
        # A whole-tree grep of every arm clone took 1.5 h on one case (BSD grep, 254 patterns); the clones differ from the base
        # only by the overlay, so the base is read in full and each arm only for its overlay.
        arms = [d for d in (BENCH / tid).iterdir() if d.is_dir() and d.name != "base" and (d / "CLAUDE.md").exists()]
        roots = [str(base)] + [str(d / o) for d in arms for o in OVERLAY if (d / o).exists()]
        present = _present(roots, probes)
        _MARKERS[tid] = [x for x in probes if x not in present]
    return _MARKERS[tid]


_INDEX = {}


def index(snap):
    if snap not in _INDEX:
        skip = {"node_modules", "graphify-out", "graft", ".serena", ".git"}
        files = []
        for p in snap.rglob("*"):
            if p.is_file() and not (skip & set(p.relative_to(snap).parts)):
                files.append(str(p.relative_to(snap)))
        _INDEX[snap] = files
    return _INDEX[snap]


def resolve(snap, p):
    """Repo-relative path for a named path that may be abbreviated (B/…, …/x/y.ts): exact, else a unique suffix."""
    p = p.lstrip("./").replace("…/", "").replace(".../", "")
    if (snap / p).is_file():
        return p
    parts = p.split("/")
    for i in range(len(parts)):
        tail = "/".join(parts[i:])
        hits = [f for f in index(snap) if f == tail or f.endswith("/" + tail)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None
    return None


def rule_cited(srcs, brief):
    """Does the brief cite one of the rule's source docs? A rule with no source (KEY=all) is never cited by an empty name."""
    return any(x["doc"] and x["doc"].split(" ")[0] in brief for x in srcs)


def used(arm, calls, n_by_tool):
    """Did the session use its arm's tool? The adapter's ARM_<F>_USED: always | mcp (any MCP call) | cli (a call whose command
    runs ARM_<F>_CLI) | cli,skill (that, or the Skill tool). None for an arm with no adapter."""
    m = META.get(stand.family(arm))
    if m is None:
        return None
    kinds = set((m.get("used") or "always").split(","))
    if "always" in kinds:
        return True
    rx = re.compile(r"\b(" + m["cli"] + r")\b") if m.get("cli") else None
    return bool(("mcp" in kinds and n_by_tool["mcp"] > 0)
                or ("cli" in kinds and rx is not None and any(rx.search(i.get("command") or "") for _, i, _ in calls))
                or ("skill" in kinds and any(n == "Skill" for n, _, _ in calls)))


def outside_paths(calls, session_dir):
    """The absolute paths a session's tool calls touched outside where it may (ALLOWED_PREFIXES, the temp dirs, its own
    session dir — Claude Code saves a large tool output under <session>/tool-results/ — and ~/.local/bin)."""
    outside = set()
    for name, inp, _ in calls:
        for v in (inp.get("file_path"), inp.get("path"), inp.get("command")):
            for p in re.findall(r"(/(?:Users|home|private|tmp|var)/[^\s'\"`)]+)", v or ""):
                p = re.sub(r"/{2,}", "/", p)   # a TMPDIR ending in "/" gives the prompt's paths a "//"
                if not p.startswith(ALLOWED_PREFIXES + ("/tmp/", "/private/tmp/", str(session_dir) + "/",
                                                         str(Path.home() / ".local/bin"))):
                    outside.add(p[:120])
    return outside


def score(tid, arm_run):
    out = BENCH / tid / "out" / arm_run
    arm = arm_run.rsplit("-", 1)[0]
    snap = BENCH / tid / arm
    truth = json.loads((stand.TASKS / f"{tid}.truth.json").read_text())
    stream = list(events(out / "stream.jsonl"))
    init = next((e for e in stream if e.get("subtype") == "init"), {})
    result = next((e for e in reversed(stream) if e.get("type") == "result"), {})
    sid = init.get("session_id") or result.get("session_id")
    proj = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(snap))
    main_tr = proj / f"{sid}.jsonl"
    subs = sorted((proj / sid / "subagents").glob("*.jsonl")) if sid and (proj / sid / "subagents").exists() else []
    main_calls = tool_log(events(main_tr)) if main_tr.exists() else tool_log(stream)
    sub_calls = [c for s in subs for c in tool_log(events(s))]
    calls = main_calls + sub_calls

    # cost by source (characters of tool results that entered some agent's context)
    by_src = defaultdict(int)
    n_by_tool = Counter()
    for name, inp, res in calls:
        by_src[source_of(name, inp)] += len(res)
        n_by_tool[name if not name.startswith("mcp__") else "mcp"] += 1

    # brief
    brief_p = out / "brief.md"
    brief = brief_p.read_text() if brief_p.exists() else ""
    sections = re.split(r"^## ", brief, flags=re.M)
    change = next((s for s in sections if s.lower().startswith("1. files to change")), "")
    raw_change = {m.group(1) for m in PATH_RE.finditer(change)}
    raw_any = {m.group(1) for m in PATH_RE.finditer(brief)}
    named_change = {resolve(snap, p) or p for p in raw_change}
    named_any = {resolve(snap, p) or p for p in raw_any}
    missing_paths = sorted(p for p in raw_any if resolve(snap, p) is None
                           and not any(p.endswith(c["path"]) for c in truth.get("created", [])))
    code_truth, test_truth = set(truth["code"]), set(truth.get("tests", []))
    alt = set(truth.get("acceptable", []))
    change_code = {p for p in named_change if p not in test_truth}

    # rules: sighting in any tool result; cited doc in the brief
    all_results = "\n".join(norm(r) for _, _, r in calls)
    rules = []
    for r in truth["rules"]:
        # a family counts when any of its sources is sighted or cited
        srcs = r.get("sources") or [{"doc": r["doc"], "quote": r["quote"]}]
        sighted = any(norm(x["quote"])[:60] in all_results for x in srcs)
        cited = rule_cited(srcs, brief)
        rules.append({"id": r["id"], "sighted": sighted, "doc_cited": cited})

    # audit
    raw = (main_tr.read_text() if main_tr.exists() else "") + "".join(x.read_text() for x in subs)
    flags = [f"leak marker: {mk}" for mk in markers(tid) if mk in raw]
    outside = outside_paths(calls, proj / str(sid))
    if outside:
        flags.append(f"paths outside: {sorted(outside)[:6]}")
    tool_used = used(arm, calls, n_by_tool)

    usage = result.get("usage", {})
    s = {
        "arm_run": arm_run, "session": sid, "subagents": len(subs),
        "cost_usd": result.get("total_cost_usd"), "duration_s": round((result.get("duration_ms") or 0) / 1000),
        "turns": result.get("num_turns"), "usage": {k: usage.get(k) for k in (
            "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")},
        "model_usage": result.get("modelUsage"),
        "tool_calls": dict(n_by_tool), "result_chars_by_source": dict(sorted(by_src.items(), key=lambda x: -x[1])),
        "brief_chars": len(brief),
        "files": {"code_recall_change": f"{len(change_code & code_truth)}/{len(code_truth)}",
                  "code_recall_any": f"{len(named_any & code_truth)}/{len(code_truth)}",
                  "tests_named": f"{len(named_any & test_truth)}/{len(test_truth)}",
                  "change_list": sorted(named_change),
                  "precision_raw": f"{len(named_change & (code_truth | test_truth))}/{len(named_change)}",
                  "precision_alt": f"{len(named_change & (code_truth | test_truth | alt))}/{len(named_change)}"},
        "missing_paths": missing_paths, "rules": rules, "tool_used": tool_used, "audit_flags": flags,
    }
    (out / "score.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
    return s


if __name__ == "__main__":
    tid = sys.argv[1]
    for ar in sys.argv[2:]:
        s = score(tid, ar)
        print(f"== {ar}: ${s['cost_usd']:.2f} · {s['duration_s']} s · {s['turns']} turns · subagents {s['subagents']} · "
              f"tool used {s['tool_used']} · brief {s['brief_chars']} chars")
        print("   files:", s["files"])
        print("   rules:", s["rules"])
        print("   tool calls:", s["tool_calls"])
        print("   result chars:", s["result_chars_by_source"])
        print("   usage:", s["usage"])
        print("   missing paths:", s["missing_paths"][:6], "| audit:", s["audit_flags"] or "clean")
