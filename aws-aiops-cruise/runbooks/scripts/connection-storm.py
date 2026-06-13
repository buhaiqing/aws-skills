#!/usr/bin/env python3
"""connection-storm.py — RDS/Aurora connection saturation patrol."""

from __future__ import annotations

import argparse
import json
import os
import uuid

from _aws_native import audit_rds_proxy
from _report import build_aiops_context
from _shared import get_metric_stats, jq_filter, log, make_incident, preflight, resolve_output_dir, resolve_scope_ids, run_aws


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

    data = run_aws(["aws", "rds", "describe-db-instances"], region)
    for db in jq_filter(data or {}, ".DBInstances[]"):
        ident = db.get("DBInstanceIdentifier", "")
        if scope and not any(ident in s for s in scope):
            continue
        max_conn = 0
        for pgroup in [db.get("DBParameterGroups", [{}])[0].get("DBParameterGroupName")]:
            if pgroup:
                params = run_aws(
                    ["aws", "rds", "describe-db-parameters", "--db-parameter-group-name", pgroup],
                    region,
                )
                if params:
                    for par in params.get("Parameters", []):
                        if par.get("ParameterName") == "max_connections":
                            try:
                                max_conn = int(par.get("ParameterValue", 0))
                            except ValueError:
                                pass
        stats = get_metric_stats(
            region, "AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", ident, hours=1
        )
        cur = stats.get("max") or stats.get("avg") or 0
        pct = (cur / max_conn * 100) if max_conn else cur
        if pct >= 70 or cur >= 70:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="RDS",
                    resource_id=ident,
                    rule_id="RDS-CONN-01",
                    title=f"Connection storm risk: {cur:.0f} connections"
                    + (f" ({pct:.0f}% of max)" if max_conn else ""),
                    level="CRITICAL" if pct >= 85 else "WARNING",
                    metric="DatabaseConnections",
                    current_value=cur,
                    threshold_warning=70,
                    threshold_critical=85,
                    recommendation="Kill idle sessions; pool at app; RDS Proxy; runbook 06",
                )
            )

    incidents.extend(audit_rds_proxy(region, scope, run_id, customer))

    report = {
        "run_id": run_id,
        "scenario": "connection_storm",
        "incidents": incidents,
        "aiops_context": build_aiops_context(
            run_id=run_id,
            trace_id=run_id[:12],
            status="partial" if incidents else "ok",
            summary=f"Connection storm check: {len(incidents)} findings",
            incidents=incidents,
            region=region,
        ),
    }
    path = out_dir / f"connstorm-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Wrote {path}")
    return 1 if any(i["level"] == "CRITICAL" for i in incidents) else 0


if __name__ == "__main__":
    raise SystemExit(main())
