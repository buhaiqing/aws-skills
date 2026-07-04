"""AWS-native read-only collectors (split from _aws_native.py)."""

from collectors.compute import (
    audit_autoscaling_headroom,
    audit_ecs_drift,
    audit_eks_nodes,
    audit_xray_service_graph,
)
from collectors.data import audit_rds_performance_insights, audit_rds_proxy
from collectors.edge import (
    audit_cloudfront,
    audit_cloudfront_s3_origins,
    audit_route53_health_checks,
    audit_waf_blocked,
)
from collectors.governance import (
    audit_acm_expiry,
    audit_cloudwatch_alarms,
    audit_compute_optimizer,
    audit_config_compliance,
    audit_devops_guru,
    audit_guardduty,
    audit_security_hub,
)
from collectors.registry import collect_aws_native_insights

__all__ = [
    "audit_acm_expiry",
    "audit_autoscaling_headroom",
    "audit_cloudfront",
    "audit_cloudfront_s3_origins",
    "audit_cloudwatch_alarms",
    "audit_compute_optimizer",
    "audit_config_compliance",
    "audit_devops_guru",
    "audit_ecs_drift",
    "audit_eks_nodes",
    "audit_guardduty",
    "audit_rds_performance_insights",
    "audit_rds_proxy",
    "audit_route53_health_checks",
    "audit_security_hub",
    "audit_waf_blocked",
    "audit_xray_service_graph",
    "collect_aws_native_insights",
]
