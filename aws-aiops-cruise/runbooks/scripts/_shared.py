#!/usr/bin/env python3
"""Shared helpers for aws-aiops-cruise runbook scripts."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_env = Path(__file__).resolve().parents[3] / ".env"
if _env.exists():
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

W = "w"
C = "c"

PRODUCTS: list[dict[str, Any]] = [
    {
        "category": "compute",
        "name": "EC2",
        "list": ["aws", "ec2", "describe-instances"],
        "jq": ".Reservations[].Instances[] | select(.State.Name != \"terminated\")",
        "id": "InstanceId",
        "metrics": {
            "CPUUtilization": {W: 70, C: 85},
            "StatusCheckFailed": {W: 0.5, C: 1},
        },
        "namespace": "AWS/EC2",
        "dim": "InstanceId",
    },
    {
        "category": "network",
        "name": "ALB",
        "list": ["aws", "elbv2", "describe-load-balancers"],
        "jq": '.LoadBalancers[] | select(.Type=="application")',
        "id": "LoadBalancerArn",
        "metrics": {
            "UnHealthyHostCount": {W: 1, C: 3},
            "TargetResponseTime": {W: 1.0, C: 3.0},
            "HTTPCode_Target_5XX_Count": {W: 10, C: 50},
        },
        "namespace": "AWS/ApplicationELB",
        "dim": "LoadBalancer",
        "dim_from_arn": True,
        "statistic": {"HTTPCode_Target_5XX_Count": "Sum"},
    },
    {
        "category": "network",
        "name": "NLB",
        "list": ["aws", "elbv2", "describe-load-balancers"],
        "jq": '.LoadBalancers[] | select(.Type=="network")',
        "id": "LoadBalancerArn",
        "metrics": {
            "ActiveFlowCount": {W: 10000, C: 50000},
            "ProcessedBytes": {W: 1e9, C: 5e9},
        },
        "namespace": "AWS/NetworkELB",
        "dim": "LoadBalancer",
        "dim_from_arn": True,
    },
    {
        "category": "database",
        "name": "RDS",
        "list": ["aws", "rds", "describe-db-instances"],
        "jq": ".DBInstances[]",
        "id": "DBInstanceIdentifier",
        "metrics": {
            "CPUUtilization": {W: 75, C: 85},
            "DatabaseConnections": {W: 70, C: 85},
            "FreeStorageSpace": {W: 5_000_000_000, C: 2_000_000_000},
            "ReadLatency": {W: 0.02, C: 0.1},
        },
        "namespace": "AWS/RDS",
        "dim": "DBInstanceIdentifier",
        "metric_invert": {"FreeStorageSpace": True},
    },
    {
        "category": "database",
        "name": "ElastiCache",
        "list": ["aws", "elasticache", "describe-cache-clusters"],
        "jq": ".CacheClusters[]",
        "id": "CacheClusterId",
        "metrics": {
            "CPUUtilization": {W: 70, C: 85},
            "DatabaseMemoryUsagePercentage": {W: 75, C: 90},
            "CurrConnections": {W: 1000, C: 5000},
        },
        "namespace": "AWS/ElastiCache",
        "dim": "CacheClusterId",
    },
    {
        "category": "network",
        "name": "NAT",
        "list": ["aws", "ec2", "describe-nat-gateways"],
        "jq": '.NatGateways[] | select(.State=="available")',
        "id": "NatGatewayId",
        "metrics": {
            "ActiveConnectionCount": {W: 50000, C: 100000},
            "ErrorPortAllocation": {W: 0, C: 1},
        },
        "namespace": "AWS/NATGateway",
        "dim": "NatGatewayId",
    },
    {
        "category": "compute",
        "name": "Lambda",
        "list": ["aws", "lambda", "list-functions"],
        "jq": ".Functions[]",
        "id": "FunctionName",
        "metrics": {
            "Errors": {W: 5, C: 20},
            "Throttles": {W: 1, C: 10},
            "Duration": {W: 3000, C: 10000},
        },
        "namespace": "AWS/Lambda",
        "dim": "FunctionName",
        "statistic": {"Errors": "Sum", "Throttles": "Sum"},
    },
    {
        "category": "api",
        "name": "ApiGateway",
        "list": ["aws", "apigateway", "get-rest-apis"],
        "jq": ".items[]",
        "id": "id",
        "metrics": {
            "5XXError": {W: 5, C: 50},
            "4XXError": {W: 50, C: 200},
            "Count": {W: 100000, C: 500000},
        },
        "namespace": "AWS/ApiGateway",
        "dim": "ApiName",
        "dim_field": "name",
        "statistic": {"5XXError": "Sum", "4XXError": "Sum", "Count": "Sum"},
    },
    {
        "category": "database",
        "name": "DynamoDB",
        "list": ["aws", "dynamodb", "list-tables"],
        "jq": ".TableNames[]",
        "id_flat": True,
        "metrics": {
            "ConsumedReadCapacityUnits": {W: 1000, C: 5000},
            "ThrottledRequests": {W: 1, C: 10},
        },
        "namespace": "AWS/DynamoDB",
        "dim": "TableName",
        "statistic": {"ThrottledRequests": "Sum"},
    },
]

COMMAND_TRACE: list[str] = []


def log(level: str, msg: str) -> None:
    print(f"[{level}] {msg}", flush=True)


def run_aws(cmd: list[str], region: str, retries: int = 3) -> dict[str, Any] | None:
    full = list(cmd)
    if "--region" not in full:
        full.extend(["--region", region])
    if "--output" not in full:
        full.extend(["--output", "json"])
    cmd_str = " ".join(full[:8])
    if cmd_str not in COMMAND_TRACE:
        COMMAND_TRACE.append(cmd_str)
    for attempt in range(retries):
        try:
            r = subprocess.run(full, capture_output=True, text=True, check=False, timeout=120)
            if r.returncode == 0:
                return json.loads(r.stdout) if r.stdout.strip() else {}
            if "Throttling" in (r.stderr or "") and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            log("WARN", f"cmd failed ({r.returncode}): {cmd_str}… {(r.stderr or '')[:180]}")
            break
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            log("ERROR", str(e))
            break
    return run_aws_boto3(full, region)


def _parse_iso_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_dimension_string(raw: str) -> list[dict[str, str]]:
    import re

    return [
        {"Name": m.group(1), "Value": m.group(2)}
        for m in re.finditer(r"Name=([^,\s]+),Value=([^\s]+)", raw)
    ]


def run_aws_boto3(cmd: list[str], region: str) -> dict[str, Any] | None:
    """Fallback after CLI failure (repo dual-path convention)."""
    if len(cmd) < 3 or cmd[0] != "aws":
        return None
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        log("WARN", "boto3 not installed — skip SDK fallback")
        return None

    svc, op = cmd[1], cmd[2]
    method = op.replace("-", "_")
    boto_region = "us-east-1" if svc in ("cloudfront", "s3", "s3api") else region
    if svc == "s3api":
        svc = "s3"
    client = boto3.client(svc, region_name=boto_region)

    kwargs: dict[str, Any] = {}
    i = 3
    while i < len(cmd):
        token = cmd[i]
        if not token.startswith("--") or token in ("--output", "--region"):
            i += 1
            continue
        key = token[2:].replace("-", "_")
        if i + 1 < len(cmd) and not cmd[i + 1].startswith("--"):
            val = cmd[i + 1]
            i += 2
        else:
            val = True
            i += 1
        if key == "dimensions":
            kwargs["Dimensions"] = _parse_dimension_string(str(val))
            continue
        if key == "statistics":
            kwargs["Statistics"] = [val] if isinstance(val, str) else val
            continue
        if key == "start_time":
            kwargs["StartTime"] = _parse_iso_time(str(val))
            continue
        if key == "end_time":
            kwargs["EndTime"] = _parse_iso_time(str(val))
            continue
        if key == "period":
            kwargs["Period"] = int(val)
            continue
        if key == "group_name":
            kwargs["Group"] = val
            continue
        if key == "id" and svc == "cloudfront":
            kwargs["Id"] = val
            continue
        boto_key = "".join(part.capitalize() for part in key.split("_"))
        kwargs[boto_key] = val

    trace = f"boto3 {svc} {method}"
    if trace not in COMMAND_TRACE:
        COMMAND_TRACE.append(trace)
    try:
        return getattr(client, method)(**kwargs)
    except (ClientError, BotoCoreError, AttributeError, ValueError, TypeError) as exc:
        log("WARN", f"boto3 fallback failed {svc}.{method}: {exc}")
        return None


def jq_filter(data: dict | list, jq_expr: str) -> list[dict]:
    try:
        r = subprocess.run(
            ["jq", "-c", jq_expr],
            input=json.dumps(data),
            capture_output=True,
            text=True,
            check=True,
        )
        return [json.loads(ln) for ln in r.stdout.splitlines() if ln.strip()]
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def resolve_scope_ids(
    region: str,
    resource_group: str = "",
    tag_key: str = "",
    tag_value: str = "",
) -> set[str]:
    ids: set[str] = set()
    if resource_group:
        token = None
        while True:
            cmd = [
                "aws",
                "resource-groups",
                "list-group-resources",
                "--group-name",
                resource_group,
            ]
            if token:
                cmd.extend(["--next-token", token])
            data = run_aws(cmd, region)
            if not data:
                break
            for item in data.get("Resources", data.get("ResourceIdentifiers", [])):
                rid = item.get("Identifier") or item.get("ResourceArn") or item.get("ResourceId") or ""
                if rid:
                    ids.add(rid)
                    ids.add(rid.split("/")[-1])
            token = data.get("NextToken") or data.get("PaginationToken")
            if not token:
                break
    if tag_key and tag_value:
        token = None
        while True:
            cmd = [
                "aws",
                "resourcegroupstaggingapi",
                "get-resources",
                "--tag-filters",
                f"Key={tag_key},Values={tag_value}",
            ]
            if token:
                cmd.extend(["--pagination-token", token])
            data = run_aws(cmd, region)
            if not data:
                break
            for m in data.get("ResourceTagMappingList", []):
                arn = m.get("ResourceARN", "")
                if arn:
                    ids.add(arn)
                    ids.add(arn.split("/")[-1])
            token = data.get("PaginationToken")
            if not token:
                break
    return ids


def reverse_lookup_scope(region: str, resource_id: str) -> tuple[str, str, set[str]]:
    """From a resource ID, derive tag scope and expanded scope IDs."""
    tag_key, tag_value = "", ""
    extra: set[str] = {resource_id}
    prefix = resource_id.split("-")[0] if "-" in resource_id else resource_id[:2]

    if resource_id.startswith("i-"):
        data = run_aws(["aws", "ec2", "describe-instances", "--instance-ids", resource_id], region)
        if data:
            for inst in jq_filter(data, ".Reservations[].Instances[]"):
                extra.add(inst.get("InstanceId", ""))
                for t in inst.get("Tags", []):
                    if t.get("Key") in ("Environment", "customer", "Customer", "app"):
                        tag_key, tag_value = t["Key"], t["Value"]
    elif resource_id.startswith("db-"):
        data = run_aws(["aws", "rds", "describe-db-instances", "--db-instance-identifier", resource_id], region)
        if data and data.get("DBInstances"):
            db = data["DBInstances"][0]
            extra.add(db.get("DBInstanceArn", ""))
            for t in db.get("TagList", []):
                if t.get("Key") in ("Environment", "customer", "Customer"):
                    tag_key, tag_value = t["Key"], t["Value"]
    elif "loadbalancer" in resource_id or resource_id.startswith("arn:"):
        arn = resource_id if resource_id.startswith("arn:") else None
        if arn:
            extra.add(arn)
            lbs = run_aws(["aws", "elbv2", "describe-load-balancers", "--load-balancer-arns", arn], region)
            if lbs and lbs.get("LoadBalancers"):
                for t in lbs["LoadBalancers"][0].get("Tags", []) or []:
                    if t.get("Key") in ("Environment", "customer", "Customer"):
                        tag_key, tag_value = t["Key"], t["Value"]

    scope = resolve_scope_ids(region, "", tag_key, tag_value) if tag_key else extra
    return tag_key, tag_value, scope | extra


def resource_in_scope(resource_id: str, scope_ids: set[str]) -> bool:
    if not scope_ids:
        return False
    if resource_id in scope_ids:
        return True
    return any(resource_id in s or s in resource_id for s in scope_ids)


def alb_dimension(arn: str) -> str:
    return arn.split(":loadbalancer:")[-1] if ":loadbalancer:" in arn else arn


def get_metric_stats(
    region: str,
    namespace: str,
    metric: str,
    dim_name: str,
    dim_value: str,
    hours: int = 6,
    statistic: str = "Average",
) -> dict[str, float | None]:
    end = datetime.now(UTC)
    start = end - timedelta(hours=hours)
    stats_flag = statistic if statistic in ("Sum", "Maximum", "Minimum") else "Average"
    data = run_aws(
        [
            "aws",
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            namespace,
            "--metric-name",
            metric,
            "--dimensions",
            f"Name={dim_name},Value={dim_value}",
            "--start-time",
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--end-time",
            end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--period",
            "300",
            "--statistics",
            stats_flag,
            "Maximum" if stats_flag != "Maximum" else "Average",
        ],
        region,
    )
    if not data or not data.get("Datapoints"):
        return {"avg": None, "max": None, "sum": None}
    dps = sorted(data["Datapoints"], key=lambda x: x["Timestamp"])
    avgs = [p["Average"] for p in dps if "Average" in p]
    maxs = [p["Maximum"] for p in dps if "Maximum" in p]
    sums = [p["Sum"] for p in dps if "Sum" in p]
    return {
        "avg": sum(avgs) / len(avgs) if avgs else None,
        "max": max(maxs) if maxs else None,
        "sum": sum(sums) if sums else None,
    }


def get_wow_change(
    region: str,
    namespace: str,
    metric: str,
    dim_name: str,
    dim_value: str,
) -> float | None:
    """Week-over-week percent change (same 6h window)."""
    now = datetime.now(UTC)
    cur = get_metric_stats(region, namespace, metric, dim_name, dim_value, hours=6)
    old_end = now - timedelta(days=7)
    old_start = old_end - timedelta(hours=6)
    data = run_aws(
        [
            "aws",
            "cloudwatch",
            "get-metric-statistics",
            "--namespace",
            namespace,
            "--metric-name",
            metric,
            "--dimensions",
            f"Name={dim_name},Value={dim_value}",
            "--start-time",
            old_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--end-time",
            old_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "--period",
            "300",
            "--statistics",
            "Average",
        ],
        region,
    )
    if not data or not data.get("Datapoints"):
        return None
    old_avg = sum(p["Average"] for p in data["Datapoints"] if "Average" in p) / max(
        len(data["Datapoints"]), 1
    )
    cur_v = cur.get("avg")
    if cur_v is None or old_avg == 0:
        return None
    return round((cur_v - old_avg) / old_avg * 100, 2)


def level_for_value(value: float | None, thresholds: dict, invert: bool = False) -> str | None:
    if value is None:
        return None
    w, c = thresholds.get(W), thresholds.get(C)
    if invert:
        if c is not None and value < c:
            return "CRITICAL"
        if w is not None and value < w:
            return "WARNING"
        return None
    if c is not None and value >= c:
        return "CRITICAL"
    if w is not None and value >= w:
        return "WARNING"
    return None


def make_incident(
    *,
    run_id: str,
    customer: str,
    region: str,
    resource_type: str,
    resource_id: str,
    rule_id: str,
    title: str,
    level: str,
    metric: str,
    current_value: float | None,
    threshold_warning: float | None = None,
    threshold_critical: float | None = None,
    recommendation: str = "",
    wow_percent: float | None = None,
) -> dict[str, Any]:
    ts = datetime.now(UTC).isoformat()
    dedup_key = f"{customer}:{resource_type}:{resource_id}:{rule_id}:{ts[:10]}"
    inc: dict[str, Any] = {
        "incident_id": str(uuid.uuid4()),
        "schema_version": "1.0.0",
        "customer": customer,
        "timestamp": ts,
        "run_id": run_id,
        "level": level,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "region": region,
        "rule_id": rule_id,
        "rule_version": "1.0.0",
        "title": title,
        "dedup_key": dedup_key,
        "metric": metric,
        "current_value": current_value,
        "threshold_warning": threshold_warning,
        "threshold_critical": threshold_critical,
        "recommendation": recommendation,
    }
    if wow_percent is not None:
        inc["wow_percent"] = wow_percent
    return inc


def resolve_output_dir(base: str | None = None) -> Path:
    root = Path(base or os.environ.get("CRUISE_OUTPUT_DIR", "audit-results"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def preflight(region: str) -> dict[str, Any]:
    COMMAND_TRACE.clear()
    ident = run_aws(["aws", "sts", "get-caller-identity"], region)
    if not ident:
        raise SystemExit("[ERROR] Pre-flight failed: aws sts get-caller-identity")
    for dep in ("jq",):
        if subprocess.run(["which", dep], capture_output=True).returncode != 0:
            raise SystemExit(f"[ERROR] Missing dependency: {dep}")
    return ident


def _iter_product_items(prod: dict, data: dict) -> list[tuple[str, str]]:
    """Yield (resource_id, metric_dimension_value) pairs."""
    if prod.get("id_flat"):
        names = data.get("TableNames", [])
        return [(n, n) for n in names]
    items = jq_filter(data, prod["jq"]) if prod.get("jq") else []
    out = []
    for item in items:
        if isinstance(item, str):
            out.append((item, item))
        else:
            rid = item.get(prod["id"], "")
            dim = item.get(prod.get("dim_field", prod["id"]), rid)
            out.append((rid, dim))
    return out


def collect_inventory(region: str, scope_ids: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for prod in PRODUCTS:
        data = run_aws(prod["list"], region)
        if not data:
            counts[prod["name"]] = 0
            continue
        pairs = _iter_product_items(prod, data)
        if scope_ids:
            pairs = [(r, d) for r, d in pairs if resource_in_scope(r, scope_ids)]
        counts[prod["name"]] = len(pairs)
    return counts


def parallel_metric_scan(
    region: str,
    scope_ids: set[str],
    run_id: str,
    customer: str,
    *,
    enable_wow: bool = True,
    max_workers: int = 8,
) -> tuple[list[dict], dict[str, dict[str, dict[str, float | None]]], list[dict]]:
    """Returns (incidents, signals, risk_evidence)."""
    from _inference import build_risk_evidence

    incidents: list[dict] = []
    signals: dict[str, dict[str, dict[str, float | None]]] = {}
    risk_evidence: list[dict] = []
    tasks: list[tuple] = []

    for prod in PRODUCTS:
        data = run_aws(prod["list"], region)
        if not data:
            continue
        for rid, dim_value in _iter_product_items(prod, data):
            if not rid or (scope_ids and not resource_in_scope(rid, scope_ids)):
                continue
            if prod.get("dim_from_arn"):
                dim_value = alb_dimension(rid)
            for metric, thr in prod.get("metrics", {}).items():
                tasks.append((prod, rid, dim_value, metric, thr))

    def _one(args):
        prod, rid, dim_value, metric, thr = args
        stat_map = prod.get("statistic", {})
        stat = stat_map.get(metric, "Average")
        stats = get_metric_stats(
            region, prod["namespace"], metric, prod["dim"], dim_value, statistic=stat
        )
        if stat == "Sum":
            val = stats.get("sum")
        else:
            val = stats.get("max") if stats.get("max") is not None else stats.get("avg")
        wow = get_wow_change(region, prod["namespace"], metric, prod["dim"], dim_value) if enable_wow else None
        return prod, rid, metric, thr, val, wow

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [pool.submit(_one, t) for t in tasks]
        for fut in as_completed(futs):
            try:
                prod, rid, metric, thr, val, wow = fut.result()
            except Exception as e:
                log("WARN", f"metric task failed: {e}")
                continue
            pname = prod["name"]
            signals.setdefault(pname, {}).setdefault(rid, {})[metric] = val
            invert = prod.get("metric_invert", {}).get(metric, False)
            level = level_for_value(val, thr, invert=invert)
            if wow is not None and wow > 50 and level is None:
                level = "WARNING"
            if level:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type=pname,
                        resource_id=rid,
                        rule_id=f"METRIC-{pname}-{metric}",
                        title=f"{pname} {metric} threshold breach"
                        + (f" (WoW +{wow}%)" if wow and wow > 30 else ""),
                        level=level,
                        metric=metric,
                        current_value=val,
                        threshold_warning=thr.get(W),
                        threshold_critical=thr.get(C),
                        recommendation=f"See inference-rules.md for {pname}",
                        wow_percent=wow,
                    )
                )
            risk_evidence.append(
                build_risk_evidence(
                    pname,
                    rid,
                    metric,
                    val,
                    threshold_w=thr.get(W),
                    threshold_c=thr.get(C),
                    wow_pct=wow,
                )
            )
    return incidents, signals, risk_evidence
