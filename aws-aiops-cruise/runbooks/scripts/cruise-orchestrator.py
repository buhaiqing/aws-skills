#!/usr/bin/env python3
"""cruise-orchestrator.py — route scenarios to workflow runbooks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

from _shared import log, resolve_output_dir

SCENARIO_MAP = {
    "daily_check": ("daily-health-check.py", "workflow"),
    "weekly_capacity": ("capacity-planning.py", "workflow"),
    "pre_launch": ("pre-launch-check.py", "workflow"),
    "emergency": ("emergency-troubleshoot.py", "agent"),
    "user_query": ("emergency-troubleshoot.py", "agent"),
}


def dispatch(scenario: str, scripts_dir: Path, extra_args: list[str]) -> dict:
    runbook = SCENARIO_MAP.get(scenario, "daily-health-check.py")
    path = scripts_dir / runbook
    if not path.exists():
        return {"runbook": runbook, "exit_code": -1, "error": f"not found: {path}"}
    cmd = [sys.executable, str(path), *extra_args]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=False)
    return {
        "runbook": runbook,
        "exit_code": r.returncode,
        "duration_seconds": round(time.time() - t0, 2),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", default="daily_check")
    p.add_argument("--output-dir", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--symptom", default="")
    args, rest = p.parse_known_args()

    scripts_dir = Path(__file__).parent
    out = resolve_output_dir(args.output_dir or None)
    dispatch_id = str(uuid.uuid4())

    extra = []
    if args.resource_group:
        extra.extend(["--resource-group", args.resource_group])
    if args.tag_key:
        extra.extend(["--tag-key", args.tag_key, "--tag-value", args.tag_value])
    if args.region:
        extra.extend(["--region", args.region])
    if args.symptom:
        extra.extend(["--symptom", args.symptom])
    extra.extend(["--non-interactive", "--output-dir", str(out)])
    extra.extend(rest)

    result = dispatch(args.scenario, scripts_dir, extra)
    log_entry = {"dispatch_id": dispatch_id, "scenario": args.scenario, **result}
    with (out / "dispatch-log.jsonl").open("a") as f:
        f.write(json.dumps(log_entry) + "\n")
    log("INFO", f"dispatch {args.scenario} -> {result}")
    return max(0, result.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
