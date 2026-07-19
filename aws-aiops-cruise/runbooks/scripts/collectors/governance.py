"""Governance & insight collectors (CloudWatch alarms, Guru, Security Hub, Config, CO)."""

from __future__ import annotations

import json
from typing import Any

from _shared import make_incident, resource_in_scope, run_aws

def audit_cloudwatch_alarms(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    """Resources in ALARM state — AWS-native proactive signal."""
    incidents: list[dict] = []
    token = None
    while True:
        cmd = ["aws", "cloudwatch", "describe-alarms", "--state-value", "ALARM"]
        if token:
            cmd.extend(["--next-token", token])
        data = run_aws(cmd, region)
        if not data:
            break
        for alarm in data.get("MetricAlarms", []):
            name = alarm.get("AlarmName", "")
            dims = {d["Name"]: d["Value"] for d in alarm.get("Dimensions", [])}
            if scope_ids and not any(resource_in_scope(v, scope_ids) for v in dims.values()):
                continue
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="CloudWatch",
                    resource_id=name,
                    rule_id="CW-ALARM-01",
                    title=f"CloudWatch alarm in ALARM: {name}",
                    level="CRITICAL" if "critical" in name.lower() else "WARNING",
                    metric=alarm.get("MetricName", "AlarmState"),
                    current_value=1.0,
                    recommendation=f"Investigate {alarm.get('Namespace')}/{alarm.get('MetricName')}; "
                    f"check alarm history via aws-cloudwatch-ops",
                )
            )
        token = data.get("NextToken")
        if not token:
            break
    return incidents

def audit_devops_guru(region: str, run_id: str, customer: str) -> list[dict]:
    """DevOps Guru proactive/reactive insights (RDS, Lambda, etc.)."""
    incidents: list[dict] = []
    for op, label in (
        (["aws", "devops-guru", "list-proactive-insights", "--max-results", "15"], "proactive"),
        (["aws", "devops-guru", "list-reactive-insights", "--max-results", "15"], "reactive"),
    ):
        data = run_aws(op, region)
        if not data:
            continue
        key = "ProactiveInsights" if "proactive" in label else "ReactiveInsights"
        for ins in data.get(key, []):
            status = ins.get("Status", "")
            if status not in ("ONGOING", "OPEN"):
                continue
            iid = ins.get("Id", "")
            sev = ins.get("Severity", "MEDIUM")
            level = "CRITICAL" if sev in ("CRITICAL", "HIGH") else "WARNING"
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="DevOpsGuru",
                    resource_id=iid or label,
                    rule_id="DG-INSIGHT-01",
                    title=(ins.get("Name") or f"DevOps Guru {label} insight")[:120],
                    level=level,
                    metric="InsightSeverity",
                    current_value=1.0,
                    recommendation="Review DevOps Guru recommendation detail; correlate CloudWatch",
                )
            )
    return incidents

def audit_security_hub(region: str, run_id: str, customer: str) -> tuple[list[dict], dict[str, dict[str, Any]]]:
    incidents: list[dict] = []
    signals: dict[str, dict[str, Any]] = {}
    # Security Hub is often us-east-1 for API; try requested region first
    filters = {
        "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
        "SeverityLabel": [{"Value": "CRITICAL", "Comparison": "EQUALS"}],
    }
    import json

    data = run_aws(
        [
            "aws",
            "securityhub",
            "get-findings",
            "--filters",
            json.dumps(filters),
            "--max-results",
            "20",
        ],
        region,
    )
    if not data:
        return incidents, {"SecurityHub": signals}
    findings = data.get("Findings", [])
    if findings:
        for f in findings:
            fid = f.get("Id", "")
            signals[fid] = {"ComplianceStatus": f.get("Compliance", {}).get("ComplianceStatus", "UNKNOWN"), "WorkflowStatus": f.get("WorkflowStatus", ""), "FirstObservedAt": f.get("FirstObservedAt", ""), "Title": f.get("Title", ""), "ProductName": f.get("ProductName", ""), "SeverityLabel": f.get("SeverityLabel", "")}
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="SecurityHub",
                resource_id="aggregate",
                rule_id="SH-CRIT-01",
                title=f"Security Hub: {len(findings)} ACTIVE CRITICAL findings (sample)",
                level="CRITICAL",
                metric="CriticalFindings",
                current_value=float(len(findings)),
                recommendation="Delegate aws-securityhub-ops; map to ASFF compliance controls",
            )
        )
    return incidents, {"SecurityHub": signals}

def audit_config_compliance(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    rules = run_aws(["aws", "config", "describe-config-rules"], region)
    if not rules:
        return incidents
    for rule in rules.get("ConfigRules", [])[:15]:
        name = rule.get("ConfigRuleName", "")
        comp = run_aws(
            ["aws", "config", "describe-compliance-by-config-rule", "--config-rule-name", name],
            region,
        )
        if not comp:
            continue
        for result in comp.get("ComplianceByConfigRules", []):
            if result.get("Compliance", {}).get("ComplianceType") == "NON_COMPLIANT":
                count = result.get("Compliance", {}).get("ComplianceContributorCount", {})
                nc = count.get("CappedCount", 1)
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="Config",
                        resource_id=name,
                        rule_id="CFG-NC-01",
                        title=f"Config rule NON_COMPLIANT: {name} ({nc} resources)",
                        level="WARNING",
                        metric="NonCompliantCount",
                        current_value=float(nc),
                        recommendation="aws-config-ops describe-compliance-by-resource; remediate via AI_ASSIST",
                    )
                )
                break
    return incidents[:10]

def audit_guardduty(region: str, run_id: str, customer: str) -> tuple[list[dict], dict[str, dict[str, Any]]]:
    incidents: list[dict] = []
    signals: dict[str, dict[str, Any]] = {}
    detectors = run_aws(["aws", "guardduty", "list-detectors"], region)
    if not detectors:
        return incidents, {"GuardDuty": signals}
    for det_id in detectors.get("DetectorIds", []):
        findings = run_aws(
            [
                "aws", "guardduty", "list-findings",
                "--detector-id", det_id,
                "--finding-criteria",
                json.dumps({
                    "Criterion": {
                        "Severity": {"Gte": 7},
                        "RecordState": {"Eq": "ACTIVE"},
                    }
                }),
                "--max-results", "20",
            ],
            region,
        )
        if not findings:
            continue
        fids = findings.get("FindingIds", [])
        if not fids:
            continue
        detail = run_aws(
            [
                "aws", "guardduty", "get-findings",
                "--finding-ids", *fids[:5],
            ],
            region,
        )
        for f in (detail or {}).get("Findings", []):
            sev = f.get("Severity", 0)
            title = f.get("Title", "")[:120]
            ftype = f.get("Type", "")
            level = "CRITICAL" if sev >= 8 else "WARNING"
            fid = f.get("Id", det_id)[:128]
            signals[fid] = {"Severity": sev, "Type": f.get("Type", ""), "ServiceName": f.get("Service", {}).get("ServiceName", ""), "CreatedAt": f.get("CreatedAt", ""), "UpdatedAt": f.get("UpdatedAt", "")}
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="GuardDuty",
                    resource_id=fid,
                    rule_id="GD-HIGH-01",
                    title=f"GuardDuty HIGH+ finding: {title}",
                    level=level,
                    metric="FindingSeverity",
                    current_value=float(sev),
                    recommendation=f"Type: {ftype}; delegate aws-guardduty-ops for investigation",
                )
            )
    return incidents, {"GuardDuty": signals}

def audit_compute_optimizer(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    status = run_aws(["aws", "compute-optimizer", "get-enrollment-status"], region)
    if not status or status.get("status") != "Active":
        return incidents
    recs = run_aws(
        ["aws", "compute-optimizer", "get-ec2-instance-recommendations", "--max-results", "50"],
        region,
    )
    if not recs:
        return incidents
    for r in recs.get("instanceRecommendations", []):
        iid = r.get("instanceArn", "").split("/")[-1]
        if scope_ids and not resource_in_scope(iid, scope_ids):
            continue
        if r.get("finding") in ("OVER_PROVISIONED", "UNDER_PROVISIONED"):
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="EC2",
                    resource_id=iid,
                    rule_id="CO-EC2-01",
                    title=f"Compute Optimizer: {r.get('finding')} — {iid}",
                    level="INFO",
                    metric="OptimizerFinding",
                    current_value=1.0,
                    recommendation=f"Current {r.get('currentInstanceType')} → suggested "
                    f"{(r.get('recommendationOptions') or [{}])[0].get('instanceType', 'N/A')}",
                )
            )
    return incidents

def audit_acm_expiry(region: str, scope_ids: set[str], run_id: str, customer: str) -> tuple[list[dict], dict[str, dict[str, Any]]]:
    """ACM certificate expiry detection — DaysToExpiry <= 30 (WARNING) or <= 7 (CRITICAL)."""
    from datetime import datetime, timezone

    incidents: list[dict] = []
    signals: dict[str, dict[str, Any]] = {}
    data = run_aws(["aws", "acm", "list-certificates"], region)
    if not data:
        return incidents, {"ACM": signals}
    now = datetime.now(timezone.utc)
    for cert in data.get("CertificateSummaryList", []):
        not_after_str = cert.get("NotAfter")
        if not not_after_str:
            continue
        not_after = datetime.fromisoformat(not_after_str.replace("Z", "+00:00"))
        days = (not_after - now).days
        if days > 30:
            continue
        cert_arn = cert.get("CertificateArn", "")
        domain = cert.get("DomainName", "")
        in_use = cert.get("InUseBy", [])
        if scope_ids:
            if domain in scope_ids:
                pass
            elif any(resource_in_scope(u, scope_ids) for u in in_use):
                pass
            else:
                continue
        level = "CRITICAL" if days <= 7 else "WARNING"
        signals[cert_arn] = {"DomainName": domain, "NotAfter": not_after.timestamp(), "NotAfterDays": days, "InUseBy": in_use}
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="ACM",
                resource_id=cert_arn,
                rule_id="ACM-EXP-01",
                title=f"ACM certificate expiring in {days} days: {domain}",
                level=level,
                metric="DaysToExpiry",
                current_value=float(days),
                recommendation="Request renewal via aws-acm-ops; delegate to aws-route53-ops for DNS validation",
            )
        )
    return incidents, {"ACM": signals}

