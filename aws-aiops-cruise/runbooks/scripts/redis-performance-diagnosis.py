#!/usr/bin/env python3
"""redis-performance-diagnosis.py — ElastiCache memory/eviction patrol."""

from __future__ import annotations

import argparse
import json
import os
import uuid

from _report import build_aiops_context
from _shared import W, C, get_metric_stats, jq_filter, level_for_value, log, make_incident, preflight, resolve_output_dir, resolve_scope_ids, run_aws


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

    data = run_aws(["aws", "elasticache", "describe-cache-clusters", "--show-cache-node-info"], region)
    for cluster in jq_filter(data or {}, ".CacheClusters[]"):
        cid = cluster.get("CacheClusterId", "")
        if scope and not any(cid in s for s in scope):
            continue
        for metric, thr in {
            "DatabaseMemoryUsagePercentage": {W: 75, C: 90},
            "CurrConnections": {W: 1000, C: 5000},
            "Evictions": {W: 1, C: 100},
        }.items():
            stat = "Sum" if metric == "Evictions" else "Average"
            stats = get_metric_stats(
                region, "AWS/ElastiCache", metric, "CacheClusterId", cid, hours=6, statistic=stat
            )
            val = stats.get("sum") if metric == "Evictions" else (stats.get("max") or stats.get("avg"))
            level = level_for_value(val, thr)
            if level:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ElastiCache",
                        resource_id=cid,
                        rule_id=f"CACHE-{metric[:4].upper()}-01",
                        title=f"ElastiCache {metric} breach on {cid}",
                        level=level,
                        metric=metric,
                        current_value=val,
                        threshold_warning=thr.get(W),
                        threshold_critical=thr.get(C),
                        recommendation="Scale node type; review hot keys; aws-elasticache-ops",
                    )
                )

    report = {
        "run_id": run_id,
        "scenario": "elasticache_performance",
        "incidents": incidents,
        "aiops_context": build_aiops_context(
            run_id=run_id,
            trace_id=run_id[:12],
            status="partial" if incidents else "ok",
            summary=f"ElastiCache patrol: {len(incidents)} findings",
            incidents=incidents,
            region=region,
        ),
    }
    path = out_dir / f"elasticache-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Wrote {path}")
    return 1 if any(i["level"] == "CRITICAL" for i in incidents) else 0


if __name__ == "__main__":
    raise SystemExit(main())
