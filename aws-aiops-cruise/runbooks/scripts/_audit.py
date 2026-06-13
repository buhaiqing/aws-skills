#!/usr/bin/env python3
"""Security + compliance read-only audits."""

from __future__ import annotations

from typing import Any

from _shared import make_incident, run_aws, jq_filter

SENSITIVE_PORTS = {22, 3389, 3306, 5432, 6379, 9200, 27017}


def audit_public_sg_rules(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    data = run_aws(["aws", "ec2", "describe-security-groups"], region)
    if not data:
        return incidents
    for sg in data.get("SecurityGroups", []):
        sgid = sg.get("GroupId", "")
        if scope_ids and sgid not in scope_ids and not any(sgid in s for s in scope_ids):
            # also match if any instance in scope uses this SG — simplified: audit all in region if scope empty
            pass
        for perm in sg.get("IpPermissions", []):
            from_port = perm.get("FromPort")
            to_port = perm.get("ToPort", from_port)
            for r in perm.get("IpRanges", []) + perm.get("Ipv6Ranges", []):
                cidr = r.get("CidrIp") or r.get("CidrIpv6") or ""
                if cidr not in ("0.0.0.0/0", "::/0"):
                    continue
                ports = range(from_port or 0, (to_port or from_port or 0) + 1)
                hit = SENSITIVE_PORTS.intersection(ports) if from_port else SENSITIVE_PORTS
                if hit or from_port is None:
                    incidents.append(
                        make_incident(
                            run_id=run_id,
                            customer=customer,
                            region=region,
                            resource_type="SG",
                            resource_id=sgid,
                            rule_id="SG-PUB-01",
                            title=f"SG {sgid} exposes sensitive port(s) to internet",
                            level="CRITICAL",
                            metric="PublicIngress",
                            current_value=float(min(hit) if hit else 0),
                            recommendation="Restrict CIDR; delegate aws-vpc-ops after user confirm",
                        )
                    )
                    break
    return incidents


def audit_acm_expiry(region: str, days: int, run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    data = run_aws(["aws", "acm", "list-certificates", "--certificate-statuses", "ISSUED"], region)
    if not data:
        return incidents
    for summary in data.get("CertificateSummaryList", []):
        arn = summary.get("CertificateArn", "")
        detail = run_aws(["aws", "acm", "describe-certificate", "--certificate-arn", arn], region)
        if not detail:
            continue
        cert = detail.get("Certificate", {})
        not_after = cert.get("NotAfter")
        if not not_after:
            continue
        from datetime import UTC, datetime

        if hasattr(not_after, "timestamp"):
            exp = not_after
        else:
            exp = datetime.fromisoformat(str(not_after).replace("Z", "+00:00"))
        delta = (exp - datetime.now(UTC)).days
        if delta <= days:
            incidents.append(
                make_incident(
                    run_id=run_id,
                    customer=customer,
                    region=region,
                    resource_type="ACM",
                    resource_id=arn.split("/")[-1],
                    rule_id="ACM-EXP-01",
                    title=f"Certificate expires in {delta} days",
                    level="CRITICAL" if delta <= 7 else "WARNING",
                    metric="DaysToExpiry",
                    current_value=float(delta),
                    threshold_warning=30,
                    threshold_critical=7,
                    recommendation="Renew via aws-acm-ops; verify ALB listener attachment",
                )
            )
    return incidents


def audit_guardduty(region: str, run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    det = run_aws(["aws", "guardduty", "list-detectors"], region)
    if not det or not det.get("DetectorIds"):
        return incidents
    detector = det["DetectorIds"][0]
    findings = run_aws(
        [
            "aws",
            "guardduty",
            "list-findings",
            "--detector-id",
            detector,
            "--finding-criteria",
            '{"Criterion":{"severity":{"Gte":7},"service.archived":{"Eq":["false"]}}}',
        ],
        region,
    )
    if not findings:
        return incidents
    ids = findings.get("FindingIds", [])
    if ids:
        incidents.append(
            make_incident(
                run_id=run_id,
                customer=customer,
                region=region,
                resource_type="OTHER",
                resource_id=detector,
                rule_id="GD-HIGH-01",
                title=f"GuardDuty: {len(ids)} HIGH/CRITICAL unarchived findings",
                level="CRITICAL" if len(ids) >= 3 else "WARNING",
                metric="FindingCount",
                current_value=float(len(ids)),
                recommendation="Review aws-guardduty-ops; escalate if production",
            )
        )
    return incidents


def audit_alb_target_health(region: str, scope_ids: set[str], run_id: str, customer: str) -> list[dict]:
    incidents: list[dict] = []
    lbs = run_aws(["aws", "elbv2", "describe-load-balancers"], region)
    if not lbs:
        return incidents
    for lb in lbs.get("LoadBalancers", []):
        arn = lb.get("LoadBalancerArn", "")
        if scope_ids and not resource_in_scope(arn, scope_ids):
            continue
        tgs = run_aws(["aws", "elbv2", "describe-target-groups", "--load-balancer-arn", arn], region)
        if not tgs:
            continue
        for tg in tgs.get("TargetGroups", []):
            tg_arn = tg.get("TargetGroupArn", "")
            health = run_aws(
                ["aws", "elbv2", "describe-target-health", "--target-group-arn", tg_arn],
                region,
            )
            if not health:
                continue
            bad = [
                h
                for h in health.get("TargetHealthDescriptions", [])
                if h.get("TargetHealth", {}).get("State") != "healthy"
            ]
            if bad:
                incidents.append(
                    make_incident(
                        run_id=run_id,
                        customer=customer,
                        region=region,
                        resource_type="ALB",
                        resource_id=arn,
                        rule_id="ALB-TGT-01",
                        title=f"Target group has {len(bad)} unhealthy target(s)",
                        level="CRITICAL" if len(bad) >= 3 else "WARNING",
                        metric="UnhealthyTargetCount",
                        current_value=float(len(bad)),
                        recommendation="aws elbv2 describe-target-health; check EC2/SG/listener",
                    )
                )
    return incidents


def resource_in_scope(resource_id: str, scope_ids: set[str]) -> bool:
    if not scope_ids:
        return True
    if resource_id in scope_ids:
        return True
    return any(resource_id in s or s in resource_id for s in scope_ids)
