#!/usr/bin/env python3
"""auto-scaling-optimization.py — ASG headroom + Compute Optimizer."""

from __future__ import annotations

import argparse
import json
import os
import uuid

from _aws_native import audit_autoscaling_headroom, audit_compute_optimizer
from _report import build_aiops_context
from _shared import log, preflight, resolve_output_dir, resolve_scope_ids


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--output-dir", default="")
    args = p.parse_args()

    region = args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    run_id = str(uuid.uuid4())
    customer = args.resource_group or f"{args.tag_key}={args.tag_value}"
    out_dir = resolve_output_dir(args.output_dir or None)
    preflight(region)
    scope = resolve_scope_ids(region, args.resource_group, args.tag_key, args.tag_value)

    incidents = []
    incidents.extend(audit_autoscaling_headroom(region, scope, run_id, customer))
    incidents.extend(audit_compute_optimizer(region, scope, run_id, customer))

    report = {
        "run_id": run_id,
        "scenario": "autoscaling_optimization",
        "incidents": incidents,
        "aiops_context": build_aiops_context(
            run_id=run_id,
            trace_id=run_id[:12],
            status="ok" if not incidents else "partial",
            summary=f"ASG/Optimizer: {len(incidents)} recommendations",
            incidents=incidents,
            region=region,
        ),
    }
    path = out_dir / f"asg-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
