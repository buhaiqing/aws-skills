#!/usr/bin/env python3
"""workflow-runner.py — deterministic runbook execution (no LLM)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

from _shared import log, resolve_output_dir

RUNBOOKS = {
    "01": "daily-health-check.py",
    "02": "emergency-troubleshoot.py",
    "03": "capacity-planning.py",
    "04": "pre-launch-check.py",
    "05": "slow-query-diagnosis.py",
    "06": "connection-storm.py",
    "07": "bottleneck-localization.py",
    "08": "redis-performance-diagnosis.py",
    "09": "auto-scaling-optimization.py",
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runbook", required=True, help="01-04 or script name")
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--symptom", default="")
    args, rest = p.parse_known_args()

    script = RUNBOOKS.get(args.runbook, args.runbook)
    scripts_dir = Path(__file__).parent
    path = scripts_dir / script
    if not path.exists():
        log("ERROR", f"Runbook not found: {path}")
        return 2

    out = resolve_output_dir(args.output_dir or None)
    run_id = str(uuid.uuid4())
    cmd = [sys.executable, str(path)]
    if args.resource_group:
        cmd.extend(["--resource-group", args.resource_group])
    if args.tag_key:
        cmd.extend(["--tag-key", args.tag_key, "--tag-value", args.tag_value])
    if args.region:
        cmd.extend(["--region", args.region])
    if args.symptom:
        cmd.extend(["--symptom", args.symptom])
    cmd.extend(["--non-interactive", "--output-dir", str(out), *rest])

    t0 = time.time()
    rc = subprocess.call(cmd)
    audit = {
        "workflow_run_id": run_id,
        "runbook": script,
        "exit_code": rc,
        "duration_seconds": round(time.time() - t0, 2),
    }
    with (out / "workflow-log.jsonl").open("a") as f:
        f.write(json.dumps(audit) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
