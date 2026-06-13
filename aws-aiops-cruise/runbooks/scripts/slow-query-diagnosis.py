#!/usr/bin/env python3
"""slow-query-diagnosis.py — RDS Performance Insights + latency metrics."""

from __future__ import annotations

import argparse
import os
import sys
import uuid

from _aws_native import audit_rds_performance_insights
from _report import build_aiops_context
from _shared import get_metric_stats, jq_filter, log, make_incident, preflight, resolve_output_dir, resolve_scope_ids, run_aws, W, C


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--db-instance", default="", help="Optional single RDS identifier")
    p.add_argument("--output-dir", default="")
    args = p.parse_args()

    region = args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    run_id = str(uuid.uuid4())
    out_dir = resolve_output_dir(args.output_dir or None)
    customer = args.resource_group or f"{args.tag_key}={args.tag_value}"
    preflight(region)
    scope = resolve_scope_ids(region, args.resource_group, args.tag_key, args.tag_value)
    if args.db_instance:
        scope.add(args.db_instance)

    incidents = audit_rds_performance_insights(region, scope, run_id, customer)
    data = run_aws(["aws", "rds", "describe-db-instances"], region)
    if data:
        for db in jq_filter(data, ".DBInstances[]"):
            ident = db.get("DBInstanceIdentifier", "")
            if scope and ident not in scope and not any(ident in s for s in scope):
                continue
            for metric in ("ReadLatency", "WriteLatency"):
                stats = get_metric_stats(region, "AWS/RDS", metric, "DBInstanceIdentifier", ident, hours=1)
                val = stats.get("max") or stats.get("avg")
                if val and val >= 0.05:
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="RDS",
                            resource_id=ident,
                            rule_id="RDS-LAT-01",
                            title=f"RDS {metric} elevated ({val:.3f}s)",
                            level="CRITICAL" if val >= 0.1 else "WARNING",
                            metric=metric,
                            current_value=val,
                            recommendation="PI top SQL; check missing indexes; aws-rds-ops",
                        )
                    )

    import json

    report = {
        "run_id": run_id,
        "scenario": "slow_query",
        "incidents": incidents,
        "aiops_context": build_aiops_context(
            run_id=run_id,
            trace_id=run_id[:12],
            status="partial" if incidents else "ok",
            summary=f"Slow query patrol: {len(incidents)} findings",
            incidents=incidents,
            region=region,
        ),
    }
    path = out_dir / f"slowquery-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Wrote {path}")
    return 1 if any(i["level"] == "CRITICAL" for i in incidents) else 0


if __name__ == "__main__":
    raise SystemExit(main())
