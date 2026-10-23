"""The context-recall skill's workspace in a user's repository: `<repo>/.context-recall/` (git-ignored by its own
.gitignore) with stand.env, cases/, prereg/ and state.json (the phase reached, the run labels, the case lists).

  workspace.py init   --repo <path> [--arms A,B]   create it with the arms chosen (default: BARE, the agent alone); refuses
                                               a path with whitespace, or an existing workspace
  workspace.py arms   --repo <path> [--json]   the arms' cards: what each tool is, and the install it takes on this machine
  workspace.py arms   --repo <path> --set A,B  change the workspace's arms (BARE is always kept)
  workspace.py add-arm --repo <path> --name N --kind plugin --plugin <dir> --skill <skill> [--cli <cmd>]
  workspace.py add-arm --repo <path> --name N --kind mcp --command <exe> [--arg <a> …]   ({repo} = the arm's clone)
  workspace.py add-arm --repo <path> --name N --kind cli --cli <cmd> [--index "<command>"]
                                               the user's own tool as an arm, written into <workspace>/arms/
  workspace.py detect --repo <path> [--json]   the task histories found; exit 3 when there is none (the prerequisite)
  workspace.py status --repo <path>            the phase and the next step
  workspace.py phase  <name> --repo <path>     record a phase reached
The kit's scripts run with BENCH_WORKSPACE=<repo>/.context-recall."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]          # skills/context-recall/scripts/ → the kit root
PHASES = {   # phase → the next step, in order
    "selftest": "run the self-test (selftest/selftest.sh) to check the arms' tools on this machine",
    "configure": "set the arms and models in stand.env; add your own tool as an arm if you want one",
    "candidates": "list past tasks with the history adapter and pick 10–20 (a tuning and a held-out set)",
    "tracing": "trace each picked task into a case (subagents with CASE_AUTHORING.md), then validate_case.py",
    "prereg": "write the preregistration: question, stages, arms, cases, metrics, analysis",
    "pilot": "run one case, every arm, one session each, and read its summary",
    "batch": "run the remaining tuning cases, one at a time",
    "judge": "calibrate the judge on two tuning cases (calibrate.sh, compare_judges.py)",
    "numbers": "read stats.py --ref BARE (and --by stage) with the reading guide",
    "calibration": "edit the docs or tool settings, then compare two labelled runs (compare_runs.py); finally the held-out cases",
}


def ws_dir(repo):
    return Path(repo).resolve() / ".context-recall"


def template():
    for n in ("stand.env.example", "stand.env.template"):
        if (KIT / n).exists():
            return KIT / n
    sys.exit("context-recall: the kit has no stand.env template")


def arm_cards(w=None):
    """One card per arm adapter — the kit's, then the user's own in the workspace w (add-arm): family, about, own, status
    (ready | install | needs), missing, install. `needs` = a command the install needs (uv, npm) is not on PATH;
    `install` = the tool itself is not installed yet."""
    pins = dict(re.findall(r"^([A-Z_]+)=(\S*)", template().read_text(), re.M))
    cards = []
    kit = sorted((KIT / "arms").glob("*.zsh"), key=lambda p: (p.stem != "BARE", p.stem))
    own = sorted((w / "arms").glob("*.zsh")) if w and (w / "arms").is_dir() else []
    for p in kit + own:
        f, text = p.stem, p.read_text()

        def field(k):
            m = re.search(rf"^ARM_{f}_{k}=(['\"])(.*)\1\s*$", text, re.M)
            return m.group(2) if m else ""
        install = re.sub(r"\$\{?([A-Z_]+)\}?", lambda m: pins.get(m.group(1)) or m.group(0), field("INSTALL"))
        missing = [n for n in field("NEEDS").split() if not shutil.which(n)]
        tool = field("BIN")
        status = "needs" if missing else "install" if (install and not tool) or (tool and not shutil.which(tool)) else "ready"
        cards.append({"family": f, "about": field("ABOUT") or field("TOOL"), "own": p in own, "status": status,
                      "missing": missing, "install": install})
    return cards


KINDS = ("plugin", "mcp", "cli")


def plugin_folder(spec):
    """--plugin: a folder (a plugin's source checkout or its install folder), or an installed plugin's id
    <plugin>@<marketplace> — resolved to its current install folder from Claude Code's installed_plugins.json."""
    if spec and "@" in spec and not Path(spec).expanduser().exists():
        cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
        f = cfg / "plugins" / "installed_plugins.json"
        installed = json.loads(f.read_text()).get("plugins", {}) if f.is_file() else {}
        if spec not in installed:
            die(f"no installed plugin {spec} (installed: {', '.join(sorted(installed)) or 'none'})")
        return Path(installed[spec][-1]["installPath"]).resolve()
    return Path(spec or ".").expanduser().resolve()


def words(*names):
    """The judge's blinding alternatives for the tool's names: each once, regex characters escaped (not "-")."""
    return "|".join(dict.fromkeys(re.sub(r"([.^$*+?{}\[\]\\|()])", r"\\\1", n) for n in names if n))


def q(s):
    """A zsh single-quoted word."""
    return "'" + str(s).replace("'", "'\\''") + "'"


def add_arm(w, a):
    """Writes the user's own tool as an arm into <workspace>/arms/: <NAME>.zsh (the adapter) and integration-<NAME>.md (the
    paragraph its clone's CLAUDE.md gets). The kit stays untouched. Exit 2 on a name taken or a tool that cannot be found."""
    name = (a.name or "").upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", name):
        die(f"the arm's name must be letters and digits only (no '-': that marks a variant): {a.name}")
    cards = {c["family"]: c for c in arm_cards(w)}
    if name in cards and not (a.replace and cards[name]["own"]):
        die(f"an arm {name} exists already (workspace.py arms)"
            + ("; --replace rewrites your own arm (e.g. a new plugin version)" if cards[name]["own"] else ""))
    pre = f"ARM_{name}_"
    if a.kind == "plugin":
        pdir = plugin_folder(a.plugin)
        pj = pdir / ".claude-plugin" / "plugin.json"
        if not pj.is_file():
            die(f"no .claude-plugin/plugin.json in {pdir}: --plugin is the plugin's folder (for an installed plugin, "
                "~/.claude/plugins/cache/<marketplace>/<plugin>/<version>)")
        plugin = json.loads(pj.read_text()).get("name") or pdir.name
        if not a.skill or not (pdir / "skills" / a.skill / "SKILL.md").is_file():
            have = sorted(p.parent.name for p in pdir.glob("skills/*/SKILL.md"))
            die(f"no skill {a.skill} in {pdir}/skills (it has: {', '.join(have) or 'none'})")
        sentence = f"the `{a.skill}` skill (the `{plugin}` plugin) along with your other tools"
        used, cli, blind = ("cli,skill" if a.cli else "skill"), a.cli or "", words(plugin, a.skill, a.cli)
        about = a.about or f"Your own tool: the {a.skill} skill of the {plugin} plugin"
        body = (f"{name}_PLUGIN_DIR={q(pdir)}\n"
                f"arm_setup_{name}() {{ [ -f ${name}_PLUGIN_DIR/.claude-plugin/plugin.json ] || fail \"the plugin of {name} "
                f"is gone: ${name}_PLUGIN_DIR\"; }}\n"
                f"arm_manifest_{name}() {{ python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get(\"version\"); "
                f"print(json.dumps({{\"tools\": {{sys.argv[2]: v}}}}))' ${name}_PLUGIN_DIR/.claude-plugin/plugin.json {q(plugin)}; }}\n"
                f"arm_session_{name}() {{ PLUGIN=(--plugin-dir ${name}_PLUGIN_DIR); [ -d ${name}_PLUGIN_DIR/bin ] && "
                f"EXTRA_PATH=${name}_PLUGIN_DIR/bin:; return 0; }}\n")
        para = (f"## {plugin}\n\nThis repository copy has the `{a.skill}` skill of the `{plugin}` plugin. Use it while you "
                f"explore a change.\n")
        binary, install = "", ""
    elif a.kind == "mcp":
        if not a.command or not shutil.which(a.command):
            die(f"the MCP server's command is not found: {a.command} (--command: an executable or a command on PATH)")
        server = name.lower()
        sentence = f"the `{server}` MCP server along with your other tools"
        used, cli, blind = "mcp", "", server
        about = a.about or f"Your own tool: the {server} MCP server ({a.command})"
        args = " ".join(q(x) for x in a.arg or [])
        body = (f"{name}_MCP_COMMAND={q(a.command)}\n{name}_MCP_ARGS=({args})   # {{repo}} = the arm's clone of the snapshot\n"
                f"arm_setup_{name}() {{ command -v ${name}_MCP_COMMAND >/dev/null || fail \"{name}: the MCP server's command "
                f"is not found: ${name}_MCP_COMMAND\"; }}\n"
                f"arm_session_{name}() {{\n  python3 -c 'import json,sys; w=sys.argv[1]; print(json.dumps({{\"mcpServers\": "
                f"{{sys.argv[2]: {{\"command\": sys.argv[3], \"args\": [x.replace(\"{{repo}}\", w) for x in sys.argv[4:]]}}}}}}))' "
                f"$W {server} ${name}_MCP_COMMAND ${name}_MCP_ARGS > $MCP\n  TOOLS+=(mcp__{server})\n}}\n")
        para = f"## {server}\n\nThe `{server}` MCP server is available in this session.\n"
        binary, install = a.command, f"put {a.command} on PATH"
    else:
        if not a.cli or not re.fullmatch(r"[\w.-]+", a.cli):
            die("--cli is the command's name, e.g. --cli mytool")
        sentence = f"the `{a.cli}` CLI along with your other tools"
        used, cli, blind = "cli", a.cli, words(a.cli)
        about = a.about or f"Your own tool: the {a.cli} command"
        body = (f"arm_setup_{name}() {{ command -v {a.cli} >/dev/null || fail \"{name}: {a.cli} is not on PATH\"; }}\n")
        if a.index:
            body += (f"{name}_INDEX={q(a.index)}   # run in the arm's clone before the sessions\n"
                     f"arm_build_{name}() {{ (cd $1 && eval \"${name}_INDEX\") >> $3 2>&1; }}\n")
        para = (f"## {a.cli}\n\nThe `{a.cli}` command is on PATH; `{a.cli} --help` lists its verbs."
                + (" Its index of this repository is built.\n" if a.index else "\n"))
        binary, install = a.cli, f"put {a.cli} on PATH"
    adapter = (f"# {name}: the user's own tool ({a.kind}), written by workspace.py add-arm — edit freely; the kit's arms/BARE.zsh\n"
               f"# lists every key and hook.\n"
               f"{pre}TOOL={q(sentence)}\n{pre}CLI={q(cli)}\n{pre}USED={q(used)}\n{pre}BLIND={q(blind)}\n"
               f"{pre}OVERLAY='CLAUDE.md'\n{pre}ABOUT={q(about)}\n{pre}NEEDS=''\n{pre}BIN={q(binary)}\n{pre}INSTALL={q(install)}\n"
               f"arm_prep_{name}() {{ cat $OWN_ARMS/integration-{name}.md >> $1/CLAUDE.md; }}\n" + body)
    (w / "arms").mkdir(exist_ok=True)
    (w / "arms" / f"{name}.zsh").write_text(adapter)
    (w / "arms" / f"integration-{name}.md").write_text(para)
    print(f"arm {name}: {w / 'arms' / (name + '.zsh')}\n"
          f"its paragraph: {w / 'arms' / ('integration-' + name + '.md')} — say there, as plainly as the kit's own\n"
          f"  (integration-TRAIL.md), what the tool does; nothing about this repository's rules\n"
          f"next: workspace.py arms --repo {w.parent} --set <the arms besides BARE>,{name}, then\n"
          f"  selftest.sh --arms BARE,{name} --own-arms {w / 'arms'} (free: the stand-in checks it runs and is scored)")


def die(msg):
    print(f"context-recall: {msg}", file=sys.stderr)
    sys.exit(2)


def chosen_arms(spec, w=None):
    """BARE first, then the arms asked for, each once; exit 2 on an arm with no adapter (kit or workspace)."""
    known = {c["family"] for c in arm_cards(w)}
    asked = [a.strip() for a in (spec or "").split(",") if a.strip()]
    bad = [a for a in asked if a.split("-")[0] not in known]
    if bad:
        print(f"context-recall: no arm adapter for {', '.join(bad)} (arms: {', '.join(sorted(known))})", file=sys.stderr)
        sys.exit(2)
    return ",".join(dict.fromkeys(["BARE", *asked]))


def set_arms(env, arms):
    return re.sub(r"^ARMS=.*$", f"ARMS={arms}", env, flags=re.M)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace")


def detect(repo):
    """The task histories of a repository: [{"source", "count", "globs"? | "dir"?}]."""
    found = []
    files = git(repo, "grep", "-l", "-z", "-E", r"^##[[:space:]]+Run[[:space:]]*$", "--", "*.md").stdout.split("\0")
    files = [f for f in files if f]
    if files:   # one glob per folder that holds task files: never a glob over every doc of the repository
        dirs = sorted({str(Path(f).parent) for f in files})
        globs = ["*.md" if d == "." else f"{d}/*.md" for d in dirs]
        found.append({"source": "taskfiles", "count": len(files), "globs": globs})
    root = Path(repo)
    staged = [p.parent for p in root.glob("*/*/feature.json")]
    if staged:
        found.append({"source": "staged", "count": len(staged), "dir": str(staged[0].parent.relative_to(root))})
    speckit = [p.parent for p in root.glob("specs/*/spec.md") if (p.parent / "tasks.md").exists()]
    if speckit:
        found.append({"source": "speckit", "count": len(speckit), "dir": "specs"})
    if shutil.which("gh"):
        p = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", "20", "--json", "number,body"],
                           cwd=repo, capture_output=True, text=True)
        if p.returncode == 0:
            n = sum(1 for pr in json.loads(p.stdout or "[]") if (pr.get("body") or "").strip())
            if n:
                found.append({"source": "pulls", "count": n})
    return found


def main():
    ap = argparse.ArgumentParser(description=" ".join(__doc__.split("\n\n")[0].split()))
    ap.add_argument("cmd", choices=["init", "arms", "add-arm", "detect", "status", "phase"])
    ap.add_argument("phase_name", nargs="?", metavar="name")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--arms", help="init: the arms to compare besides BARE, comma-separated")
    ap.add_argument("--set", help="arms: the workspace's new arms besides BARE, comma-separated")
    g = ap.add_argument_group("add-arm: the user's own tool")
    g.add_argument("--name", help="the arm's name, letters and digits (e.g. DISCOVER)")
    g.add_argument("--kind", choices=KINDS, help="plugin (a Claude Code plugin with a skill), mcp (an MCP server), cli")
    g.add_argument("--plugin", help="plugin: its folder (with .claude-plugin/plugin.json) or an installed id <plugin>@<marketplace>")
    g.add_argument("--skill", help="plugin: the skill the sessions should use")
    g.add_argument("--cli", help="cli: the command's name; plugin: the plugin's own command, if it has one")
    g.add_argument("--command", help="mcp: the server's executable")
    g.add_argument("--arg", action="append", help="mcp: one argument of the server, repeatable; {repo} = the clone")
    g.add_argument("--index", help="cli: a command that builds the tool's index, run in the arm's clone")
    g.add_argument("--about", help="one line for the arm's card")
    g.add_argument("--replace", action="store_true", help="rewrite your own arm of that name (a new plugin version)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve(); w = ws_dir(repo)
    if a.cmd in ("add-arm",) or (a.cmd == "arms" and a.set is not None):
        if not (w / "stand.env").exists():
            die(f"no workspace at {w} (workspace.py init)")
    if a.cmd == "add-arm":
        if not a.kind:
            die("add-arm needs --kind plugin | mcp | cli")
        add_arm(w, a)
    elif a.cmd == "arms" and a.set is not None:
        arms = chosen_arms(a.set, w)
        (w / "stand.env").write_text(set_arms((w / "stand.env").read_text(), arms))
        print(f"arms: {arms}\nnext: bench.sh setup (installs or checks their tools)")
    elif a.cmd == "arms":
        cards = arm_cards(w)
        if a.json:
            print(json.dumps({"arms": cards}, indent=1))
        for c in [] if a.json else cards:
            print(f"{c['family']} — {c['about']}" + ("  [your own]" if c["own"] else ""))
            if c["status"] == "ready":
                print("  ready: nothing to install")
            elif c["status"] == "install":
                print(f"  takes an install: {c['install']}")
            else:
                print(f"  needs {', '.join(c['missing'])} (not on this machine): install it, then {c['install']}")
    elif a.cmd == "init":
        arms = chosen_arms(a.arms)   # a new workspace has no own arms yet
        if re.search(r"\s", str(w)):
            print(f"context-recall: the kit cannot run on a path with whitespace: {w}", file=sys.stderr); sys.exit(2)
        if w.exists():
            print(f"context-recall: {w} exists (workspace.py status)", file=sys.stderr); sys.exit(2)
        if git(repo, "rev-parse", "--git-dir").returncode:
            print(f"context-recall: {repo} is not a git repository", file=sys.stderr); sys.exit(2)
        (w / "cases").mkdir(parents=True); (w / "prereg").mkdir()
        (w / ".gitignore").write_text("*\n")
        env = set_arms(re.sub(r"^HOST_REPO=.*$", f"HOST_REPO={repo}", template().read_text(), flags=re.M), arms)
        (w / "stand.env").write_text(env)
        (w / "state.json").write_text(json.dumps({"phase": "selftest", "labels": [], "tuning": [], "heldout": [],
                                                  "history": detect(repo)}, indent=1))
        print(f"workspace: {w}\narms: {arms}\nnext: {PHASES['selftest']}")
    elif a.cmd == "detect":
        found = detect(repo)
        if a.json:
            print(json.dumps({"sources": found}, indent=1))
        else:
            for f in found:
                where = " ".join(f.get("globs") or []) or f.get("dir")
                print(f"{f['source']}: {f['count']}" + (f" ({where})" if where else ""))
            if not found:
                print("no task history: the kit needs task texts in the repository (task files with a ## Run section, "
                      "a specs/ folder, or merged pull requests with a description) — commit subjects alone are not enough")
        sys.exit(0 if found else 3)
    else:
        if not (w / "state.json").exists():
            print(f"context-recall: no workspace at {w} (workspace.py init)", file=sys.stderr); sys.exit(2)
        state = json.loads((w / "state.json").read_text())
        if a.cmd == "phase":
            if a.phase_name not in PHASES:
                print(f"context-recall: unknown phase {a.phase_name} ({', '.join(PHASES)})", file=sys.stderr); sys.exit(2)
            state["phase"] = a.phase_name
            (w / "state.json").write_text(json.dumps(state, indent=1))
        print(f"phase: {state['phase']}\nnext: {PHASES[state['phase']]}\nlabels: {', '.join(state['labels']) or 'none'}")
        # what the disk shows, so a recorded phase is never trusted alone
        cases = sorted((w / "cases").glob("*.case.json"))
        prereg = sorted(p.name for p in (w / "prereg").glob("*.md"))
        res = w / "results"
        runs = [(d.name, sum(1 for c in d.iterdir() if (c / "summary.md").exists()))
                for d in sorted(res.iterdir()) if d.is_dir()] if res.is_dir() else []
        print(f"cases: {len(cases)} · tuning {', '.join(state['tuning']) or '-'} · held-out {', '.join(state['heldout']) or '-'}")
        print(f"prereg: {', '.join(prereg) or 'none'}")
        print("results: " + (", ".join(f"{n} ({k} case{'s' if k != 1 else ''})" for n, k in runs if k) or "none"))


if __name__ == "__main__":
    main()
