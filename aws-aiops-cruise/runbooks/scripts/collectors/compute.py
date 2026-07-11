"""Compute layer collectors (ECS, EKS, ASG, X-Ray)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from _shared import make_incident, resource_in_scope, run_aws, log

from collectors._time import json_time

def audit_ecs_drift(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    clusters = run_aws(["aws", "ecs", "list-clusters"], region)
    if not clusters:
        return incidents
    for cluster_arn in clusters.get("clusterArns", []):
        if scope_ids and not resource_in_scope(cluster_arn, scope_ids):
            continue
        svcs = run_aws(["aws", "ecs", "list-services", "--cluster", cluster_arn], region)
        if not svcs:
            continue
        for svc_arn in svcs.get("serviceArns", [])[:20]:
            desc = run_aws(
                ["aws", "ecs", "describe-services", "--cluster", cluster_arn, "--services", svc_arn],
                region,
            )
            if not desc or not desc.get("services"):
                continue
            svc = desc["services"][0]
            desired = svc.get("desiredCount", 0)
            running = svc.get("runningCount", 0)
            if desired > 0 and running < desired:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ECS",
                        resource_id=svc.get("serviceName", svc_arn),
                        rule_id="ECS-TASK-01",
                        title=f"ECS service running {running}/{desired} tasks",
                        level="CRITICAL" if running == 0 else "WARNING",
                        metric="RunningTaskDeficit",
                        current_value=float(desired - running),
                        recommendation="Check stopped tasks/stoppedReason; ECS events; underlying EC2 capacity",
                    )
                )
    return incidents

def audit_eks_nodes(region: str, scope_ids: set[str], run_id: str, customer: str) -> tuple[list[dict], dict[str, dict[str, float]]]:
    incidents: list[dict] = []
    signals: dict[str, dict[str, float]] = {}
    clusters = run_aws(["aws", "eks", "list-clusters"], region)
    if not clusters:
        return incidents, signals
    for name in clusters.get("clusters", []):
        if scope_ids and not resource_in_scope(name, scope_ids):
            continue
        ng = run_aws(["aws", "eks", "list-nodegroups", "--cluster-name", name], region)
        if not ng:
            continue
        for ng_name in ng.get("nodegroups", []):
            desc = run_aws(
                ["aws", "eks", "describe-nodegroup", "--cluster-name", name, "--nodegroup-name", ng_name],
                region,
            )
            if not desc:
                continue
            ngd = desc.get("nodegroup", {})
            scaling = ngd.get("scalingConfig", {}) or {}
            signals[f"{name}/{ng_name}"] = {
                "NodesDesired": float(scaling.get("desiredSize", 0) or 0),
                "NodesCurrent": float(scaling.get("currentSize", 0) or 0),
                "NodesMin": float(scaling.get("minSize", 0) or 0),
                "NodesMax": float(scaling.get("maxSize", 0) or 0),
            }
            health = ngd.get("health", {}).get("issues", [])
            if health:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="EKS",
                        resource_id=f"{name}/{ng_name}",
                        rule_id="EKS-NG-01",
                        title=f"EKS nodegroup health issues: {ng_name}",
                        level="CRITICAL",
                        metric="NodegroupIssues",
                        current_value=float(len(health)),
                        recommendation="eks describe-nodegroup health; check ASG, subnet, IAM, max pods",
                    )
                )
    return incidents, {"EKS": signals}

def audit_autoscaling_headroom(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    asgs = run_aws(["aws", "autoscaling", "describe-auto-scaling-groups"], region)
    if not asgs:
        return incidents
    for asg in asgs.get("AutoScalingGroups", []):
        name = asg.get("AutoScalingGroupName", "")
        if scope_ids and not resource_in_scope(name, scope_ids):
            continue
        desired = asg.get("DesiredCapacity", 0)
        max_size = asg.get("MaxSize", 0)
        if max_size > 0 and desired >= max_size * 0.9:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="ASG",
                    resource_id=name,
                    rule_id="ASG-CAP-01",
                    title=f"ASG at {desired}/{max_size} capacity (≥90% max)",
                    level="WARNING",
                    metric="CapacityUtilization",
                    current_value=round(desired / max_size * 100, 1),
                    threshold_warning=90,
                    recommendation="Raise max or scale policy; pre-launch-check for event traffic",
                )
            )
    return incidents

def audit_xray_service_graph(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """X-Ray service graph — fault/error hotspots (read-only, last 1h)."""
    incidents: list[dict] = []
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    data = run_aws(
        [
            "aws",
            "xray",
            "get-service-graph",
            "--start-time",
            json_time(start),
            "--end-time",
            json_time(end),
        ],
        region,
    )
    if not data:
        return incidents
    for svc in data.get("Services", []):
        name = svc.get("Name", "")
        type_ = svc.get("Type", "")
        if scope_ids and name and not any(
            resource_in_scope(name, scope_ids) or name in s for s in scope_ids
        ):
            # keep API Gateway / AWS::Lambda names that match function names in scope
            if not any(resource_in_scope(part, scope_ids) for part in name.split("/")):
                continue
        summary = svc.get("SummaryStatistics", {}) or {}
        faults = summary.get("FaultCount", 0) or 0
        errors = summary.get("ErrorCount", 0) or 0
        total = summary.get("TotalCount", 0) or 0
        if total < 10:
            continue
        fault_rate = (faults + errors) / total * 100
        if fault_rate >= 5:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="XRay",
                    resource_id=name[:128],
                    rule_id="XRAY-FAULT-01",
                    title=f"X-Ray: {name} fault/error rate {fault_rate:.1f}% ({faults}+{errors}/{total})",
                    level="CRITICAL" if fault_rate >= 15 else "WARNING",
                    metric="FaultErrorRate",
                    current_value=round(fault_rate, 2),
                    threshold_warning=5,
                    threshold_critical=15,
                    recommendation="Trace downstream from this node; correlate ALB/Lambda/RDS in same window",
                )
            )
    # Store graph snippet in meta for orchestrator (optional enrichment)
    return incidents

