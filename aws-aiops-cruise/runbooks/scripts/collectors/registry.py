"""Orchestrates all AWS-native collectors."""

from __future__ import annotations

from typing import Any

from _shared import log

from collectors.compute import (
    audit_autoscaling_headroom,
    audit_ecs_drift,
    audit_eks_nodes,
    audit_xray_service_graph,
)
from collectors.block import audit_ebs_volumes
from collectors.apigw import audit_apigw_health
from collectors.data import audit_rds_performance_insights, audit_rds_proxy
from collectors.edge import (
    audit_cloudfront,
    audit_cloudfront_s3_origins,
    audit_route53_health_checks,
    audit_waf_blocked,
)
from collectors.analytics import audit_athena_cost
from collectors.ram_audit import audit_ram_shares
from collectors.secrets_audit import audit_secrets_rotation
from collectors.cloudfront_audit import audit_cloudfront_signals
from collectors.search_audit import audit_opensearch_health
from collectors.governance import (
    audit_acm_expiry,
    audit_cloudwatch_alarms,
    audit_compute_optimizer,
    audit_config_compliance,
    audit_devops_guru,
    audit_guardduty,
    audit_security_hub,
)

def collect_aws_native_insights(
    region: str,
    scope_ids: set[str],
    run_id: str,
    customer: str,
    *,
    enable_pi: bool = True,
    enable_guru: bool = True,
    enable_cloudfront: bool = True,
    enable_xray: bool = False,
    enable_rds_proxy: bool = True,
) -> tuple[list[dict], dict[str, Any], dict[str, Any]]:
    """Run all AWS-native collectors; return (incidents, summary-meta, signals).

    `signals` carries per-service signal dicts (e.g. {"EKS": {ng_id: {...}}})
    so inference rules in `_inference.py` have populated inputs at runtime.
    """
    incidents: list[dict] = []
    meta: dict[str, Any] = {"collectors": []}
    signals: dict[str, Any] = {}

    collectors = [
        ("cloudwatch_alarms", lambda: audit_cloudwatch_alarms(region, scope_ids, run_id, customer)),
        ("acm", lambda: audit_acm_expiry(region, scope_ids, run_id, customer)),
        ("security_hub", lambda: audit_security_hub(region, run_id, customer)),
        ("guardduty", lambda: audit_guardduty(region, run_id, customer)),
        ("config", lambda: audit_config_compliance(region, scope_ids, run_id, customer)),
        ("route53_hc", lambda: audit_route53_health_checks(run_id, customer)),
        ("waf", lambda: audit_waf_blocked(region, scope_ids, run_id, customer)),
        ("ecs", lambda: audit_ecs_drift(region, scope_ids, run_id, customer)),
        ("eks", lambda: audit_eks_nodes(region, scope_ids, run_id, customer)),
        ("asg", lambda: audit_autoscaling_headroom(region, scope_ids, run_id, customer)),
        ("compute_optimizer", lambda: audit_compute_optimizer(region, scope_ids, run_id, customer)),
        ("ebs", lambda: audit_ebs_volumes(region, scope_ids, run_id, customer)),
        ("apigw", lambda: audit_apigw_health(region, scope_ids, run_id, customer)),
    ]
    if enable_pi:
        collectors.append(("rds_pi", lambda: audit_rds_performance_insights(region, scope_ids, run_id, customer)))
    if enable_guru:
        collectors.append(("devops_guru", lambda: audit_devops_guru(region, run_id, customer)))
    if enable_cloudfront:
        collectors.append(("cloudfront", lambda: audit_cloudfront(scope_ids, run_id, customer)))
        collectors.append(("cloudfront_s3", lambda: audit_cloudfront_s3_origins(scope_ids, run_id, customer)))
        collectors.append(("cloudfront_signals", lambda: audit_cloudfront_signals(scope_ids, run_id, customer)))
    collectors.append(("athena", lambda: audit_athena_cost(region, scope_ids, run_id, customer)))
    collectors.append(("ram", lambda: audit_ram_shares(region, scope_ids, run_id, customer)))
    collectors.append(("secrets", lambda: audit_secrets_rotation(region, scope_ids, run_id, customer)))
    collectors.append(("opensearch", lambda: audit_opensearch_health(region, scope_ids, run_id, customer)))
    if enable_rds_proxy:
        collectors.append(("rds_proxy", lambda: audit_rds_proxy(region, scope_ids, run_id, customer)))
    if enable_xray:
        collectors.append(("xray", lambda: audit_xray_service_graph(region, scope_ids, run_id, customer)))

    for name, fn in collectors:
        try:
            found = fn()
            # Collectors may return either a bare incident list (legacy) or a
            # (incidents, signals_dict) tuple. The latter folds its per-service
            # signal dicts into `signals` so inference rules can consume them
            # (e.g. EKS, Athena, RAM, SecretsManager, CloudFront, OpenSearch).
            if isinstance(found, tuple) and len(found) == 2:
                inc, signal_map = found
                incidents.extend(inc)
                for layer, resources in signal_map.items():
                    signals.setdefault(layer, {}).update(resources)
                meta["collectors"].append({"name": name, "findings": len(inc)})
            else:
                incidents.extend(found)
                meta["collectors"].append({"name": name, "findings": len(found)})
        except Exception as e:
            log("WARN", f"collector {name} failed: {e}")
            meta["collectors"].append({"name": name, "error": str(e)[:100]})

    return incidents, meta, signals

