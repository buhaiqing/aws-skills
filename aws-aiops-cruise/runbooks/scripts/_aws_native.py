#!/usr/bin/env python3
"""
AWS-native AIOps data collectors — facade for backward-compatible imports.

Implementation lives in collectors/ (governance, edge, compute, data).
"""

from __future__ import annotations

from collectors import (
    audit_autoscaling_headroom,
    audit_compute_optimizer,
    audit_rds_performance_insights,
    audit_rds_proxy,
    collect_aws_native_insights,
)

__all__ = [
    "audit_autoscaling_headroom",
    "audit_compute_optimizer",
    "audit_rds_performance_insights",
    "audit_rds_proxy",
    "collect_aws_native_insights",
]
