"""Shared test helpers: the demo repository, a workspace with its own stand.env, and a runner whose `claude` is the
self-test's stand-in and whose environment carries none of the caller's stand settings."""
import os
import re
import subprocess
from pathlib import Path

STAND = Path(__file__).resolve().parent.parent
STANDIN = STAND / "selftest" / "bin"
# the settings a caller's environment could leak into a test run
ENV_KEYS = {"HOST_REPO", "BENCH_DATA", "BENCH", "RESULTS", "ARMS", "RUNS", "PAR", "BRIEF_MODEL", "JUDGE_MODEL",
            "REQUEST_FIELD", "TEST_DIRS", "DOCS_RE", "BASE_STRIP", "LEAK_PROBE_FILES", "SUMMARY", "LEGACY_IDS",
            "BENCH_WORKSPACE", "RUN_LABEL", "KEY", "DOCS_PATCH", "DOCS_GLOBS", "HISTORY_GLOB", "FROM", "CLEAN", "STAND"}


def run(cmd, env=None, cwd=None):
    """Runs cmd with the stand-in claude first on PATH; returns the CompletedProcess (text)."""
    e = {k: v for k, v in os.environ.items() if k not in ENV_KEYS}
    e["PATH"] = f"{STANDIN}:{e.get('PATH', '')}"
    e.update(env or {})
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=e, capture_output=True, text=True)


def demo_repo(tmp: Path) -> Path:
    """The self-test's synthetic repository, built fresh under tmp."""
    r = Path(tmp) / "repo"
    p = run([STAND / "selftest" / "make_demo_repo.sh", r])
    if p.returncode:
        raise RuntimeError(p.stderr)
    return r


def template() -> Path:
    for name in ("stand.env.example", "stand.env.template"):
        if (STAND / name).exists():
            return STAND / name
    raise FileNotFoundError("no stand.env template")


def stand_module(name: str):
    """Imports a stand script as a module under a throwaway workspace, so the test needs no stand.env of its own."""
    import importlib
    import sys
    import tempfile
    ws = Path(tempfile.mkdtemp())
    (ws / "stand.env").write_text(template().read_text())
    os.environ["BENCH_WORKSPACE"] = str(ws)
    if str(STAND) not in sys.path:
        sys.path.insert(0, str(STAND))
    sys.modules.pop("stand", None)
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def workspace(tmp: Path, host: Path, **env) -> Path:
    """A workspace dir with a stand.env from the template: HOST_REPO=host, BENCH_DATA under tmp, and the keys given."""
    w = Path(tmp) / "ws"
    w.mkdir(parents=True, exist_ok=True)
    keys = {"HOST_REPO": str(host), "BENCH_DATA": str(Path(tmp) / "data"), "ARMS": "BARE", "RUNS": "1", **env}
    text = template().read_text()
    for k, v in keys.items():
        if re.search(rf"^{k}=", text, re.M):
            text = re.sub(rf"^{k}=.*$", f"{k}={v}", text, flags=re.M)
        else:
            text += f"{k}={v}\n"
    (w / "stand.env").write_text(text)
    return w
