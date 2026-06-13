#!/usr/bin/env python3
"""capacity-planning.py — 7/30-day trend + headroom (read-only)."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

from _report import build_aiops_context, render_markdown_report
from _shared import (
    COMMAND_TRACE,
    PRODUCTS,
    W,
    C,
    alb_dimension,
    jq_filter,
    log,
    preflight,
    resolve_output_dir,
    resolve_scope_ids,
    resource_in_scope,
    run_aws,
)


def _trend_metric(region: str, prod: dict, rid: str, metric: str, thr: dict, days: int) -> dict | None:
    dim = alb_dimension(rid) if prod.get("dim_from_arn") else rid
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    data = run_aws(
        [
            "aws",
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            prod["namespace"],
            "--metric-name",
            metric,
            "--dimensions",
            f"Name={prod['dim']},Value={dim}",
            "--start-time",
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--end-time",
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--period",
            "3600",
            "--statistics",
            "Average",
        ],
        region,
    )
    if not data or len(data.get("Datapoints", [])) < 2:
        return None
    vals = sorted(data["Datapoints"], key=lambda x: x["Timestamp"])
    first = vals[0].get("Average", 0)
    last = vals[-1].get("Average", 0)
    growth = (last - first) / max(days, 1)
    days_to_crit = int((thr.get(C, 100) - last) / growth) if growth > 0 else 9999
    return {
        "resource_id": rid,
        "resource_type": prod["name"],
        "metric": metric,
        "first": round(first, 2),
        "last": round(last, 2),
        "daily_growth": round(growth, 4),
        "days_to_critical": days_to_crit,
        "threshold_critical": thr.get(C),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--resource-group", default="")
    p.add_argument("--tag-key", default="")
    p.add_argument("--tag-value", default="")
    p.add_argument("--region", default="")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--output-dir", default="")
    p.add_argument("--non-interactive", action="store_true")
    args = p.parse_args()

    region = args.region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    customer = args.resource_group or f"{args.tag_key}={args.tag_value}"
    run_id = str(uuid.uuid4())
    out_dir = resolve_output_dir(args.output_dir or None)
    ident = preflight(region)
    scope_ids = resolve_scope_ids(region, args.resource_group, args.tag_key, args.tag_value)
    if not scope_ids:
        log("ERROR", "Empty scope")
        return 2

    tasks = []
    for prod in PRODUCTS:
        data = run_aws(prod["list"], region)
        if not data:
            continue
        for item in jq_filter(data, prod["jq"]):
            rid = item.get(prod["id"], "")
            if resource_in_scope(rid, scope_ids):
                for metric, thr in prod.get("metrics", {}).items():
                    tasks.append((prod, rid, metric, thr))

    trends: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_trend_metric, region, t[0], t[1], t[2], t[3], args.days) for t in tasks]
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                trends.append(r)

    at_risk = [t for t in trends if t["days_to_critical"] <= 14]
    overall = "CRITICAL" if any(t["days_to_critical"] <= 3 for t in at_risk) else (
        "WARNING" if at_risk else "PASS"
    )

    report = {
        "run_id": run_id,
        "scenario": "capacity_planning",
        "customer": customer,
        "region": region,
        "window_days": args.days,
        "overall_grade": overall,
        "trends": trends,
        "at_risk": at_risk,
        "aiops_context": build_aiops_context(
            run_id=run_id,
            trace_id=run_id[:12],
            status="ok" if overall == "PASS" else "partial",
            summary=f"Capacity: {len(at_risk)} resources may hit critical within 14d",
            incidents=[],
            region=region,
        ),
        "trace": {"commands_executed": COMMAND_TRACE[:50], "account": ident.get("Account")},
    }
    path = out_dir / f"capacity-{run_id[:8]}.json"
    path.write_text(json.dumps(report, indent=2))
    log("INFO", f"Capacity report: {path} | at_risk={len(at_risk)}")
    return 0 if overall != "CRITICAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
