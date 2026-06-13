#!/usr/bin/env python3
"""pre-launch-check.py — event readiness: health + capacity + drift gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from _shared import log, preflight, resolve_output_dir


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--traffic-multiplier", type=float, default=3.0)
    p.add_argument("--output-dir", default="")
    p.add_argument("--non-interactive", action="store_true")
    args = p.parse_args()

    region = args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    run_id = str(uuid.uuid4())
    out_dir = resolve_output_dir(args.output_dir or None)
    scripts = Path(__file__).parent
    preflight(region)

    common = ["--region", region, "--non-interactive", "--output-dir", str(out_dir)]
    if args.resource_group:
        common.extend(["--resource-group", args.resource_group])
    if args.tag_key:
        common.extend(["--tag-key", args.tag_key, "--tag-value", args.tag_value])

    steps = [
        ("daily-health-check", [sys.executable, str(scripts / "daily-health-check.py"), *common]),
        ("capacity-planning", [sys.executable, str(scripts / "capacity-planning.py"), *common, "--days", "7"]),
    ]
    results = []
    for name, cmd in steps:
        log("INFO", f"Pre-launch step: {name}")
        rc = subprocess.call(cmd)
        results.append({"step": name, "exit_code": rc})

    # Drift check (optional — topo-discovery baseline)
    repo = Path(__file__).resolve().parents[3]
    baseline = repo.parent / "aws-topo-discovery" / "scripts" / "baseline-manager.py"
    drift_rc = 0
    if baseline.exists():
        drift_rc = subprocess.call(
            [sys.executable, str(baseline), "--diff-latest", "--output-dir", str(out_dir)],
            cwd=str(repo.parent),
        )
        results.append({"step": "config-drift", "exit_code": drift_rc})

    failed = [r for r in results if r["exit_code"] not in (0, 1)]
    overall = "FAIL" if failed else ("WARNING" if any(r["exit_code"] == 1 for r in results) else "PASS")

    report = {
        "run_id": run_id,
        "scenario": "pre_launch",
        "traffic_multiplier": args.traffic_multiplier,
        "overall_grade": overall,
        "steps": results,
        "checklist": [
            {"item": "No CRITICAL health findings", "owner": "daily-health-check"},
            {"item": "No resource hits critical within 3d", "owner": "capacity-planning"},
            {"item": "No config drift vs baseline", "owner": "config-drift"},
            {
                "item": f"Manual: validate ASG max >= current_desired * {args.traffic_multiplier}",
                "owner": "human",
            },
        ],
    }
    path = out_dir / f"prelaunch-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Pre-launch report: {path} | grade={overall}")
    return 0 if overall == "PASS" else (1 if overall == "WARNING" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
