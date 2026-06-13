"""AWS-native read-only collectors (split from _aws_native.py)."""

from collectors.compute import audit_autoscaling_headroom, audit_compute_optimizer
from collectors.data import audit_rds_performance_insights, audit_rds_proxy
from collectors.registry import collect_aws_native_insights

__all__ = [
    "audit_autoscaling_headroom",
    "audit_compute_optimizer",
    "audit_rds_performance_insights",
    "audit_rds_proxy",
    "collect_aws_native_insights",
]
