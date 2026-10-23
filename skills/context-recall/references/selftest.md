# The self-test

`<kit>/selftest/selftest.sh` — the kit as it is (read-only), a temp folder with a synthetic repository of past tasks, seven
golden cases, and a stand-in `claude`; every step a user takes, then checks. No model calls, no cost, about two minutes (longer the first time:
it installs Trail into the data dir). The user's workspace is never touched.

- Run it on the workspace's arms: `selftest.sh --arms <ARMS of <repo>/.context-recall/stand.env>` (BARE alone needs no
  install). Without `--arms` it tests all four shipped arms.
- Run it in the background; report `self-test: PASS` or the failing step with the tail of its log (the log path is printed).
- A failure in `setup` names the missing tool and how to install it (uv, npm). Offer to drop that arm
  (`workspace.py arms --set …`) and go on with the tools that work; it can be added later.
- PASS → `workspace.py phase configure`.

`--real` runs the same flow with the real `claude`, without the calibration steps: by default 7 cases × 4 arms = 28
sessions and 28 judge calls, about $7 API-equivalent, drawn from the user's plan limits. `--real --cases d01,d02,d03` (12
sessions and 12 judge calls, about $3) is the cheapest look at each tool in a real session. Cost gate first.
