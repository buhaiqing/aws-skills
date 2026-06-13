#!/usr/bin/env python3
"""Chain inference + risk evidence for aws-aiops-cruise."""

from __future__ import annotations

from typing import Any

from _shared import W, C, make_incident

# Signals: resource_type -> resource_id -> metric -> value
Signals = dict[str, dict[str, dict[str, float | None]]]

SENSITIVE_PORTS = {22, 3389, 3306, 5432, 6379, 9200, 27017}


def _get(sig: Signals, rtype: str, rid: str, metric: str) -> float | None:
    return sig.get(rtype, {}).get(rid, {}).get(metric)


def _any_above(sig: Signals, rtype: str, metric: str, threshold: float) -> list[str]:
    out = []
    for rid, metrics in sig.get(rtype, {}).items():
        v = metrics.get(metric)
        if v is not None and v >= threshold:
            out.append(rid)
    return out


def apply_chain_inference(
    signals: Signals,
    *,
    run_id: str,
    customer: str,
    region: str,
    existing_rule_ids: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (extra incidents, inference markdown lines)."""
    incidents: list[dict] = []
    lines: list[str] = []

    unhealthy_albs = _any_above(signals, "ALB", "UnHealthyHostCount", 1)
    ec2_failed = _any_above(signals, "EC2", "StatusCheckFailed", 0.5)
    for alb in unhealthy_albs:
        rule = "ALB-EC2-01"
        if rule in existing_rule_ids:
            continue
        healthy_ec2 = [i for i in signals.get("EC2", {}) if i not in ec2_failed]
        if healthy_ec2:
            lines.append(
                f"- **{rule}**: ALB `{alb}` has unhealthy targets but EC2 status checks pass "
                "→ likely SG/NACL/listener path (see inference-rules.md)"
            )
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="ALB",
                    resource_id=alb,
                    rule_id=rule,
                    title="Unhealthy targets with healthy EC2 — network path suspicion",
                    level="WARNING",
                    metric="UnHealthyHostCount",
                    current_value=_get(signals, "ALB", alb, "UnHealthyHostCount"),
                    recommendation="Check SG ingress from ALB SG; verify target port listening (aws-ssm-ops optional)",
                )
            )

    for rid, metrics in signals.get("ALB", {}).items():
        lat = metrics.get("TargetResponseTime")
        if lat is not None and lat >= 1.0:
            ec2_cpus = [v for v in (signals.get("EC2", {}).get(i, {}).get("CPUUtilization") for i in signals.get("EC2", {})) if v is not None]
            if ec2_cpus and max(ec2_cpus) < 70:
                rule = "ALB-EC2-02"
                if rule not in existing_rule_ids:
                    lines.append(f"- **{rule}**: ALB `{rid}` high latency, EC2 CPU normal → check RDS/downstream")
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="ALB",
                            resource_id=rid,
                            rule_id=rule,
                            title="High ALB latency with normal EC2 CPU",
                            level="WARNING",
                            metric="TargetResponseTime",
                            current_value=lat,
                            recommendation="Inspect RDS ReadLatency/WriteLatency; ACM cert validity",
                        )
                    )

    for rid, metrics in signals.get("RDS", {}).items():
        conn = metrics.get("DatabaseConnections")
        if conn is not None and conn >= 70:
            rule = "RDS-CONN-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: RDS `{rid}` connections elevated → pool/leak check")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="RDS",
                        resource_id=rid,
                        rule_id=rule,
                        title="RDS connection count elevated",
                        level="CRITICAL" if conn >= 85 else "WARNING",
                        metric="DatabaseConnections",
                        current_value=conn,
                        threshold_warning=70,
                        threshold_critical=85,
                        recommendation="Review app connection pool; delegate aws-rds-ops for PI",
                    )
                )

    for rid, metrics in signals.get("NAT", {}).items():
        err = metrics.get("ErrorPortAllocation")
        if err is not None and err >= 1:
            rule = "NAT-PORT-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: NAT `{rid}` port allocation errors → SNAT exhaustion risk")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="NAT",
                        resource_id=rid,
                        rule_id=rule,
                        title="NAT Gateway port allocation errors",
                        level="CRITICAL",
                        metric="ErrorPortAllocation",
                        current_value=err,
                        recommendation="Add NAT GW or reduce unique outbound destinations",
                    )
                )

    # Lambda throttles + API Gateway 5xx (serverless path)
    for fn, metrics in signals.get("Lambda", {}).items():
        if (metrics.get("Throttles") or 0) >= 1:
            rule = "LAMBDA-THROTTLE-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: Lambda `{fn}` throttled → check concurrency limits / downstream")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Lambda",
                        resource_id=fn,
                        rule_id=rule,
                        title="Lambda function throttling",
                        level="WARNING",
                        metric="Throttles",
                        current_value=metrics.get("Throttles"),
                        recommendation="Raise reserved concurrency or fix slow downstream (RDS/API)",
                    )
                )

    for api, metrics in signals.get("ApiGateway", {}).items():
        e5 = metrics.get("5XXError") or 0
        if e5 >= 5:
            rule = "APIGW-5XX-01"
            if rule not in existing_rule_ids:
                lines.append(f"- **{rule}**: API `{api}` 5xx errors → check Lambda/integration timeout")
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ApiGateway",
                        resource_id=api,
                        rule_id=rule,
                        title="API Gateway 5XX elevated",
                        level="CRITICAL" if e5 >= 50 else "WARNING",
                        metric="5XXError",
                        current_value=e5,
                        recommendation="CloudWatch Logs for API GW; Lambda Errors metric correlation",
                    )
                )

    # ALB 5xx + WAF blocks (edge path) — WAF in native audit; correlate if both in report metadata
    for rid, metrics in signals.get("ALB", {}).items():
        e5 = metrics.get("HTTPCode_Target_5XX_Count") or 0
        if e5 >= 10:
            rule = "ALB-5XX-01"
            if rule not in existing_rule_ids:
                lines.append(
                    f"- **{rule}**: ALB `{rid}` target 5xx sum high → target health / app / RDS / cert"
                )
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ALB",
                        resource_id=rid,
                        rule_id=rule,
                        title="ALB target 5XX count elevated",
                        level="CRITICAL" if e5 >= 50 else "WARNING",
                        metric="HTTPCode_Target_5XX_Count",
                        current_value=e5,
                        recommendation="elbv2 describe-target-health; check WAF if 403 vs 502 pattern",
                    )
                )

    return incidents, lines


def correlate_native_findings(
    incidents: list[dict],
    *,
    run_id: str,
    customer: str,
    region: str,
    existing_rule_ids: set[str],
) -> tuple[list[dict], list[str]]:
    """Cross-link CloudFront / RDS Proxy / X-Ray findings with metric incidents."""
    extra: list[dict] = []
    lines: list[str] = []
    rules = {i["rule_id"] for i in incidents}

    if "CF-ORIGIN-01" in rules and any(i["resource_type"] == "Lambda" for i in incidents):
        lines.append(
            "- **CF-LAMBDA-URL-01**: CloudFront origin latency + Lambda errors "
            "→ check Function URL auth, timeout, and downstream RDS"
        )
    if "CF-ORIGIN-01" in rules and any("execute-api" in i.get("resource_id", "") for i in incidents):
        lines.append(
            "- **CF-APIGW-01**: CloudFront + API Gateway path "
            "→ verify stage deployment, integration timeout, WAF on edge"
        )

    if "CF-ORIGIN-01" in rules and any(i["rule_id"].startswith("METRIC-ALB") for i in incidents):
        rid = "CF-ORIGIN-01"
        if rid not in existing_rule_ids:
            lines.append(
                "- **CF-ALB-01**: CloudFront origin latency + ALB metrics abnormal "
                "→ debug origin (ALB target health) not edge cache"
            )

    if "S3-METRICS-01" in rules:
        lines.append(
            "- **S3-METRICS-01**: S3 request metrics not published "
            "→ rely on CloudFront CF-EDGE-01 or enable S3 CloudWatch request metrics"
        )

    if "CF-S3-01" in rules or "S3-PAB-01" in rules or "S3-4XX-01" in rules or "S3-5XX-01" in rules:
        if "CF-EDGE-01" in rules or "CF-ORIGIN-01" in rules or "S3-4XX-01" in rules:
            lines.append(
                "- **CF-S3-01**: CloudFront errors + S3 origin misconfig "
                "→ verify OAC/OAI, bucket policy, Block Public Access, S3 4xx/5xx metrics"
            )

    if "RDS-PROXY-AURORA-01" in rules or "RDS-PROXY-AURORA-02" in rules:
        lines.append(
            "- **RDS-PROXY-AURORA-01**: Proxy targets Aurora cluster under stress "
            "→ failover, scale ACUs, connection-storm runbook 06"
        )

    if "RDS-PROXY-01" in rules or "RDS-PROXY-02" in rules:
        if "RDS-CONN-01" in rules or any("METRIC-RDS-DatabaseConnections" in i["rule_id"] for i in incidents):
            lines.append(
                "- **RDS-PROXY-CONN-01**: Proxy + DB connection pressure "
                "→ tune max_connections percent, pool size, or RDS Proxy target group"
            )

    if "XRAY-FAULT-01" in rules:
        xray_nodes = [i for i in incidents if i["rule_id"] == "XRAY-FAULT-01"]
        if any(i["resource_type"] == "Lambda" for i in incidents):
            lines.append(
                "- **XRAY-LAMBDA-01**: X-Ray fault node + Lambda errors "
                "→ open trace map for cold start / downstream timeout"
            )
        for x in xray_nodes[:3]:
            lines.append(f"  - Hot node: `{x['resource_id']}` rate={x.get('current_value')}%")

    return extra, lines


def build_risk_evidence(
    resource_type: str,
    resource_id: str,
    metric: str,
    current: float | None,
    *,
    threshold_w: float | None,
    threshold_c: float | None,
    wow_pct: float | None = None,
    trend_daily: float | None = None,
    consecutive: int = 0,
) -> dict[str, Any]:
    """Unified risk evidence (ML off by default)."""
    static_level = "NORMAL"
    if current is not None and threshold_c is not None and current >= threshold_c:
        static_level = "CRITICAL"
    elif current is not None and threshold_w is not None and current >= threshold_w:
        static_level = "WARNING"

    risk_score = 0.0
    if static_level == "CRITICAL":
        risk_score = 0.85
    elif static_level == "WARNING":
        risk_score = 0.55
    if wow_pct is not None and wow_pct > 50:
        risk_score = min(1.0, risk_score + 0.15)
    if trend_daily is not None and trend_daily > 0 and threshold_c and current is not None:
        days_to_crit = (threshold_c - current) / trend_daily if trend_daily > 0 else None
        if days_to_crit is not None and days_to_crit <= 3:
            risk_score = max(risk_score, 0.75)

    if risk_score >= 0.75:
        risk_level = "CRITICAL"
    elif risk_score >= 0.50:
        risk_level = "WARNING"
    elif risk_score >= 0.25:
        risk_level = "INFO"
    else:
        risk_level = "NORMAL"

    ml_mode = __import__("os").environ.get("AIOPS_ML_MODE", "off")
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metric": metric,
        "current_value": current,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 3),
        "confidence": 0.9 if static_level != "NORMAL" else 0.7,
        "static_level": static_level,
        "duration": {"consecutive_points": consecutive, "duration_minutes": consecutive * 5},
        "trend": {
            "direction": "rising" if (wow_pct or 0) > 10 else "flat",
            "wow_percent": wow_pct,
            "daily_growth": trend_daily,
        },
        "ml_shadow_result": None if ml_mode == "off" else {"mode": ml_mode, "skipped": True},
        "detection_methods": ["static_threshold", "wow"] if wow_pct else ["static_threshold"],
    }
