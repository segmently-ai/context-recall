"""The stand's paths, config and arm adapters for the Python scripts — the same values lib.sh gives the shell scripts.
A value set in the environment wins over stand.env, as in lib.sh."""
import os
import re
import subprocess
import sys
from pathlib import Path

STAND = Path(__file__).resolve().parent
# the user's side: stand.env, cases/, tasks/, results/ (BENCH_WORKSPACE; default: the stand itself)
WORKSPACE = Path(os.environ.get("BENCH_WORKSPACE") or STAND)


def _env():
    out = {}
    p = WORKSPACE / "stand.env"
    if not p.exists():
        raise SystemExit(f"no {p}: copy stand.env.example to stand.env and fill it in")
    for line in p.read_text().splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)=([^\s#]*)(.*)$", line)
        if m:
            rest = m.group(3).strip()
            if rest and not rest.startswith("#"):   # as lib.sh: a value is one word, never cut off silently
                print(f"stand.env: the value of {m.group(1)} has whitespace (a value is one word; a path must have no "
                      "spaces)", file=sys.stderr)
                sys.exit(2)
            out[m.group(1)] = m.group(2)
    return out


PINS = _env()


def cfg(key, default=""):
    """A config value: the environment, else stand.env, else the default."""
    v = os.environ.get(key)
    if v is None or v == "":
        v = PINS.get(key) or default
    return v


def _path(v):
    return Path(os.path.expanduser(v))


HOST = _path(cfg("HOST_REPO") or subprocess.run(["git", "-C", str(STAND), "rev-parse", "--show-toplevel"],
                                                capture_output=True, text=True).stdout.strip())
BENCH_DATA = _path(cfg("BENCH_DATA", "~/.context-tools-bench"))
RUN_LABEL = cfg("RUN_LABEL") or None   # a run's own results/<label>/ and runs/<label>/ (lib.sh checks it is one word)
B = _path(os.environ.get("BENCH") or BENCH_DATA / "runs") / (RUN_LABEL or "")   # BENCH moves the root; a label is its subdir


def results_for(label):
    """The results dir of a run label (None: the unlabelled results/)."""
    return WORKSPACE / "results" / label if label else WORKSPACE / "results"


RESULTS = _path(cfg("RESULTS", f"results/{RUN_LABEL}" if RUN_LABEL else "results"))
RESULTS = RESULTS if RESULTS.is_absolute() else WORKSPACE / RESULTS
CASES = WORKSPACE / "cases"


def tasks_for(label):
    """The task files (request, truth) a run label was made from: tasks/<label>/, so a run's key is frozen with it."""
    return WORKSPACE / "tasks" / label if label else WORKSPACE / "tasks"


TASKS = tasks_for(RUN_LABEL)
PLUGINS = BENCH_DATA / "plugins"
TOOLS = BENCH_DATA / "tools"
ARMS = [a for a in cfg("ARMS", "BARE").split(",") if a]


def family(arm):
    """An arm's adapter family: its name up to the first "-" (TRAIL-V2 → TRAIL)."""
    return arm.split("-")[0]


_META = re.compile(r"^ARM_([A-Z0-9]+)_(CLI|USED|BLIND|OVERLAY)='([^']*)'", re.M)


def arms_meta():
    """{family: {cli, used, blind, overlay}} from the adapters' declarations (arms/<FAMILY>.zsh, single-quoted values)."""
    out = {}
    for p in sorted((STAND / "arms").glob("*.zsh")):
        for fam, key, val in _META.findall(p.read_text()):
            out.setdefault(fam, {})[key.lower()] = val
    return out
