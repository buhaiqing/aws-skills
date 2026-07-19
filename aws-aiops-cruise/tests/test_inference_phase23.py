#!/usr/bin/env python3
"""Unit tests for Phase-2/3 inference rules (Task #10 closure).

Verifies the 5 inline rule blocks added to `apply_chain_inference` in
`runbooks/scripts/_inference.py`:
  ATHENA-COST-01, RAM-SHARE-01, SEC-ROTATE-01,
  CF-ORIGIN-02, CF-CACHE-01, OS-HEAP-01, OS-SHARD-01

Each rule consumes a `signals[<svc>]` key populated by its native
collector. We feed synthetic signals and assert hit/miss + level.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _inference import apply_chain_inference, correlate_native_findings  # noqa: E402


def _run(signals: dict) -> list[dict]:
    inc, _ = apply_chain_inference(
        signals, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    return inc


def _by_rule(inc: list[dict]) -> dict:
    return {i["rule_id"]: i for i in inc}


# --- Athena: ATHENA-COST-01 -----------------------------------------------
def test_athena_miss_below_threshold():
    inc = _run({"Athena": {"wg1": {"ProcessedBytes": 1e9}}})
    assert "ATHENA-COST-01" not in {i["rule_id"] for i in inc}


def test_athena_warn_at_5e9():
    inc = _run({"Athena": {"wg1": {"ProcessedBytes": 5e9}}})
    by = _by_rule(inc)
    assert "ATHENA-COST-01" in by
    assert by["ATHENA-COST-01"]["level"] == "WARNING"


def test_athena_crit_at_2e10():
    inc = _run({"Athena": {"wg1": {"ProcessedBytes": 2e10}}})
    by = _by_rule(inc)
    assert by["ATHENA-COST-01"]["level"] == "CRITICAL"


def test_athena_absent_metric_no_fire():
    inc = _run({"Athena": {"wg1": {"ProcessedBytes": None}}})
    assert "ATHENA-COST-01" not in {i["rule_id"] for i in inc}


# --- RAM: RAM-SHARE-01 ---------------------------------------------------
def test_ram_miss_active_no_reject():
    inc = _run({"RAM": {"arn:aws:ram:x": {"ShareStatusActive": 1.0, "RejectedAssociations": 0.0}}})
    assert "RAM-SHARE-01" not in {i["rule_id"] for i in inc}


def test_ram_warn_inactive():
    inc = _run({"RAM": {"arn:aws:ram:bad": {"ShareStatusActive": 0.0, "RejectedAssociations": 0.0}}})
    by = _by_rule(inc)
    assert by["RAM-SHARE-01"]["level"] == "WARNING"


def test_ram_warn_rejected_assoc():
    inc = _run({"RAM": {"arn:aws:ram:rej": {"ShareStatusActive": 1.0, "RejectedAssociations": 2.0}}})
    by = _by_rule(inc)
    assert "RAM-SHARE-01" in by


# --- SecretsManager: SEC-ROTATE-01 ----------------------------------------
def test_secrets_miss_fresh_enabled():
    inc = _run({"SecretsManager": {"s1": {"RotationAgeDays": 30.0, "RotationEnabled": 1.0}}})
    assert "SEC-ROTATE-01" not in {i["rule_id"] for i in inc}


def test_secrets_warn_at_90():
    inc = _run({"SecretsManager": {"s1": {"RotationAgeDays": 95.0, "RotationEnabled": 1.0}}})
    by = _by_rule(inc)
    assert by["SEC-ROTATE-01"]["level"] == "WARNING"


def test_secrets_crit_at_180():
    inc = _run({"SecretsManager": {"s1": {"RotationAgeDays": 200.0, "RotationEnabled": 1.0}}})
    by = _by_rule(inc)
    assert by["SEC-ROTATE-01"]["level"] == "CRITICAL"


def test_secrets_crit_disabled():
    inc = _run({"SecretsManager": {"s1": {"RotationAgeDays": 10.0, "RotationEnabled": 0.0}}})
    by = _by_rule(inc)
    assert by["SEC-ROTATE-01"]["level"] == "CRITICAL"


# --- CloudFront: CF-ORIGIN-02 / CF-CACHE-01 ---------------------------
def test_cloudfront_miss_healthy():
    inc = _run({"CloudFront": {"D1": {"OriginLatency": 100.0, "OriginSuccessRate": 1.0, "CacheHitRate": 0.95}}})
    ids = {i["rule_id"] for i in inc}
    assert "CF-ORIGIN-02" not in ids
    assert "CF-CACHE-01" not in ids


def test_cloudfront_origin_latency_warn():
    inc = _run({"CloudFront": {"D1": {"OriginLatency": 1500.0, "OriginSuccessRate": 1.0, "CacheHitRate": 0.95}}})
    by = _by_rule(inc)
    assert "CF-ORIGIN-02" in by
    assert by["CF-ORIGIN-02"]["level"] == "WARNING"


def test_cloudfront_origin_success_crit():
    inc = _run({"CloudFront": {"D1": {"OriginLatency": 1500.0, "OriginSuccessRate": 0.9, "CacheHitRate": 0.95}}})
    by = _by_rule(inc)
    assert by["CF-ORIGIN-02"]["level"] == "CRITICAL"


def test_cloudfront_cache_miss_warn():
    inc = _run({"CloudFront": {"D1": {"OriginLatency": 100.0, "OriginSuccessRate": 1.0, "CacheHitRate": 0.5}}})
    by = _by_rule(inc)
    assert by["CF-CACHE-01"]["level"] == "WARNING"


# --- OpenSearch: OS-HEAP-01 / OS-SHARD-01 ----------------------------
def test_opensearch_miss_healthy():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "ClusterIndexWritesBlocked": 0.0, "UnassignedShards": 0.0}}})
    ids = {i["rule_id"] for i in inc}
    assert "OS-HEAP-01" not in ids
    assert "OS-SHARD-01" not in ids


def test_opensearch_heap_warn_80():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 80.0, "ClusterIndexWritesBlocked": 0.0, "UnassignedShards": 0.0}}})
    by = _by_rule(inc)
    assert by["OS-HEAP-01"]["level"] == "WARNING"


def test_opensearch_heap_crit_95():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 96.0, "ClusterIndexWritesBlocked": 0.0, "UnassignedShards": 0.0}}})
    by = _by_rule(inc)
    assert by["OS-HEAP-01"]["level"] == "CRITICAL"


def test_opensearch_shard_crit():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "ClusterIndexWritesBlocked": 1.0, "UnassignedShards": 3.0}}})
    by = _by_rule(inc)
    assert by["OS-SHARD-01"]["level"] == "CRITICAL"


def test_opensearch_heap_absent_skips():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": None, "ClusterIndexWritesBlocked": 0.0, "UnassignedShards": 0.0}}})
    assert "OS-HEAP-01" not in {i["rule_id"] for i in inc}

# --- OpenSearch: OS-MASTER-01 / OS-SNAP-01 ---------------------------
def test_opensearch_master_miss_reachable():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "MasterReachableFromNode": 1}}})
    by = _by_rule(inc)
    assert "OS-MASTER-01" not in by

def test_opensearch_master_crit_unreachable():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "MasterReachableFromNode": 0}}})
    by = _by_rule(inc)
    assert by["OS-MASTER-01"]["level"] == "CRITICAL"
    assert by["OS-MASTER-01"]["current_value"] == 0.0

def test_opensearch_master_absent_skips():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "MasterReachableFromNode": None}}})
    assert "OS-MASTER-01" not in {i["rule_id"] for i in inc}

def test_opensearch_snap_miss_none():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "AutomatedSnapshotFailure": 0.0}}})
    assert "OS-SNAP-01" not in {i["rule_id"] for i in inc}

def test_opensearch_snap_crit_failure():
    inc = _run({"OpenSearch": {"dom1": {"JVMMemoryPressure": 50.0, "AutomatedSnapshotFailure": 2.0}}})
    by = _by_rule(inc)
    assert by["OS-SNAP-01"]["level"] == "CRITICAL"
    assert by["OS-SNAP-01"]["current_value"] == 2.0



# --- Non-regression: Phase-1 rules still fire on their own keys ----
def test_phase1_still_fires_unchanged():
    # Mirror test_inference_phase1.py trigger values (GSI throttle >=1, failover=1).
    inc = _run({
        "DynamoDB": {"tbl": {"ThrottledRequests": 5, "GSIWriteThrottleEvents": 12}},
        "ElastiCache": {"cache": {"DatabaseMemoryUsagePercentage": 70, "FailoverInProgress": 1}},
    })
    ids = {i["rule_id"] for i in inc}
    assert "DYNAMO-GSI-01" in ids
    assert "EC-FAILOVER-01" in ids


# --- Cross-service correlation patterns (correlate_native_findings) ------

def _corr_run(incidents: list[dict]) -> list[str]:
    """Call correlate_native_findings and return the lines list."""
    _, lines = correlate_native_findings(
        incidents, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    return lines


def test_correlation_no_match_no_lines():
    inc = [{"rule_id": "CF-ORIGIN-01", "resource_type": "Lambda", "resource_id": "f1"}]
    lines = _corr_run(inc)
    # No cross-service correlation should fire with only CF-ORIGIN-01
    assert "R53-ALB-01" not in "\n".join(lines)


def test_correlation_r53_alb():
    inc = [
        {"rule_id": "R53-ALB-01", "resource_type": "Route53", "resource_id": "hc1"},
        {"rule_id": "CF-ORIGIN-01", "resource_type": "Lambda", "resource_id": "f1"},
    ]
    lines = _corr_run(inc)
    joined = "\n".join(lines)
    assert "R53-ALB-01" in joined
    assert "DNS mispoint" in joined


def test_correlation_waf_alb():
    inc = [
        {"rule_id": "WAF-ALB-01", "resource_type": "WAF", "resource_id": "acl1"},
        {"rule_id": "ALB-5XX-01", "resource_type": "ALB", "resource_id": "alb1"},
    ]
    lines = _corr_run(inc)
    joined = "\n".join(lines)
    assert "WAF-ALB-01" in joined
    assert "rate rule" in joined


def test_correlation_lambda_apigw():
    inc = [
        {"rule_id": "LAMBDA-THROTTLE-01", "resource_type": "Lambda", "resource_id": "f1"},
        {"rule_id": "APIGW-5XX-01", "resource_type": "ApiGateway", "resource_id": "api1"},
    ]
    lines = _corr_run(inc)
    joined = "\n".join(lines)
    assert "LAMBDA-THROTTLE-APIGW-01" in joined
    assert "concurrency limit" in joined


def test_correlation_cf_edge_cache():
    inc = [
        {"rule_id": "CF-EDGE-01", "resource_type": "CloudFront", "resource_id": "d1"},
        {"rule_id": "CF-ORIGIN-02", "resource_type": "CloudFront", "resource_id": "d1"},
    ]
    lines = _corr_run(inc)
    joined = "\n".join(lines)
    assert "CF-EDGE-CACHE-01" in joined
    assert "cache miss amplification" in joined


# --- EC2: EC2-IDLE-01 ----------------------------------------------------
def test_ec2_idle_01_hit_warn():
    # Idle >= 7d, CPU low, healthy, non-spot
    inc = _run({
        "EC2": {"i-123": {"CPUUtilization": 1.0, "StatusCheckFailed": 0.0, "InstanceLifecycle": "on-demand", "InstanceAgeDays": 8}}
    })
    by = _by_rule(inc)
    assert "EC2-IDLE-01" in by
    assert by["EC2-IDLE-01"]["level"] == "WARNING"


def test_ec2_idle_01_hit_crit():
    # Idle >= 14d
    inc = _run({
        "EC2": {"i-456": {"CPUUtilization": 0.0, "StatusCheckFailed": 0.0, "InstanceLifecycle": "on-demand", "InstanceAgeDays": 20}}
    })
    by = _by_rule(inc)
    assert "EC2-IDLE-01" in by
    assert by["EC2-IDLE-01"]["level"] == "CRITICAL"


def test_ec2_idle_01_miss_spot():
    # Spot instance — should not fire
    inc = _run({
        "EC2": {"i-789": {"CPUUtilization": 0.0, "StatusCheckFailed": 0.0, "InstanceLifecycle": "spot", "InstanceAgeDays": 20}}
    })
    assert "EC2-IDLE-01" not in {i["rule_id"] for i in inc}


def test_ec2_idle_01_miss_too_young():
    # Instance age < 1d — should not fire
    inc = _run({
        "EC2": {"i-new": {"CPUUtilization": 0.0, "StatusCheckFailed": 0.0, "InstanceLifecycle": "on-demand", "InstanceAgeDays": 0}}
    })
    assert "EC2-IDLE-01" not in {i["rule_id"] for i in inc}


def test_ec2_idle_01_miss_healthy_failed():
    # StatusCheckFailed != 0 — should not fire
    inc = _run({
        "EC2": {"i-bad": {"CPUUtilization": 1.0, "StatusCheckFailed": 1.0, "InstanceLifecycle": "on-demand", "InstanceAgeDays": 10}}
    })
    assert "EC2-IDLE-01" not in {i["rule_id"] for i in inc}


# --- ACM: ACM-CERT-01 -----------------------------------------------------
def test_acm_cert_01_hit_warn():
    inc = _run({"ACM": {"arn:aws:acm:us-east-1:123456789012:certificate/abc123": {"DomainName": "example.com", "NotAfterDays": 20, "NotAfter": 0, "InUseBy": []}}})
    by = _by_rule(inc)
    assert "ACM-CERT-01" in by
    assert by["ACM-CERT-01"]["level"] == "WARNING"


def test_acm_cert_01_hit_crit():
    inc = _run({"ACM": {"arn:aws:acm:us-east-1:123456789012:certificate/def456": {"DomainName": "api.example.com", "NotAfterDays": 5, "NotAfter": 0, "InUseBy": []}}})
    by = _by_rule(inc)
    assert "ACM-CERT-01" in by
    assert by["ACM-CERT-01"]["level"] == "CRITICAL"


def test_acm_cert_01_miss_internal():
    # .internal domain — should skip
    inc = _run({"ACM": {"arn:aws:acm:us-east-1:123456789012:certificate/int": {"DomainName": "db.internal", "NotAfterDays": 5, "NotAfter": 0, "InUseBy": []}}})
    assert "ACM-CERT-01" not in {i["rule_id"] for i in inc}


def test_acm_cert_01_miss_far_future():
    # Not expiring soon
    inc = _run({"ACM": {"arn:aws:acm:us-east-1:123456789012:certificate/xyz": {"DomainName": "safe.com", "NotAfterDays": 200, "NotAfter": 0, "InUseBy": []}}})
    assert "ACM-CERT-01" not in {i["rule_id"] for i in inc}


# --- KMS: KMS-ROTATE-01 ---------------------------------------------------
def test_kms_rotate_01_hit():
    inc = _run({"KMS": {"arn:aws:kms:us-east-1:123456789012:key/mrk-123": {"KeyRotationEnabled": False, "KeyManager": "CUSTOMER", "CreatedTimestamp": 0, "KeySpec": "SYMMETRIC_DEFAULT", "DaysSinceCreation": 400}}})
    by = _by_rule(inc)
    assert "KMS-ROTATE-01" in by
    assert by["KMS-ROTATE-01"]["level"] == "CRITICAL"


def test_kms_rotate_01_miss_aws_managed():
    # AWS-managed — should not fire
    inc = _run({"KMS": {"arn:aws:kms:us-east-1:123456789012:key/aws-managed": {"KeyRotationEnabled": False, "KeyManager": "AWS", "CreatedTimestamp": 0, "KeySpec": "SYMMETRIC_DEFAULT", "DaysSinceCreation": 999}}})
    assert "KMS-ROTATE-01" not in {i["rule_id"] for i in inc}


def test_kms_rotate_01_miss_recent():
    # Rotation disabled but < 365d old
    inc = _run({"KMS": {"arn:aws:kms:us-east-1:123456789012:key/recent": {"KeyRotationEnabled": False, "KeyManager": "CUSTOMER", "CreatedTimestamp": 0, "KeySpec": "SYMMETRIC_DEFAULT", "DaysSinceCreation": 100}}})
    assert "KMS-ROTATE-01" not in {i["rule_id"] for i in inc}


# --- SQS: SQS-DLQ-01 ------------------------------------------------------
def test_sqs_dlq_01_hit_warn():
    inc = _run({"SQS": {"https://sqs.us-east-1.amazonaws.com/123/ MyDLQ": {"QueueType": "dlq", "ApproximateNumberOfMessages": 5, "ApproximateAgeOfOldestMessage": 7200.0, "QueueName": "MyDLQ"}}})
    by = _by_rule(inc)
    assert "SQS-DLQ-01" in by
    assert by["SQS-DLQ-01"]["level"] == "WARNING"


def test_sqs_dlq_01_hit_crit():
    inc = _run({"SQS": {"https://sqs.us-east-1.amazonaws.com/123/ MyDLQ": {"QueueType": "dlq", "ApproximateNumberOfMessages": 15, "ApproximateAgeOfOldestMessage": 7200.0, "QueueName": "MyDLQ"}}})
    by = _by_rule(inc)
    assert "SQS-DLQ-01" in by
    assert by["SQS-DLQ-01"]["level"] == "CRITICAL"


def test_sqs_dlq_01_miss_too_fresh():
    # DLQ but age < 1h
    inc = _run({"SQS": {"https://sqs.us-east-1.amazonaws.com/123/ MyDLQ": {"QueueType": "dlq", "ApproximateNumberOfMessages": 5, "ApproximateAgeOfOldestMessage": 1800.0, "QueueName": "MyDLQ"}}})
    assert "SQS-DLQ-01" not in {i["rule_id"] for i in inc}


def test_sqs_dlq_01_miss_regular_queue():
    # Not a DLQ — should not fire
    inc = _run({"SQS": {"https://sqs.us-east-1.amazonaws.com/123/ MyQueue": {"QueueType": "regular", "ApproximateNumberOfMessages": 5, "ApproximateAgeOfOldestMessage": 7200.0, "QueueName": "MyQueue"}}})
    assert "SQS-DLQ-01" not in {i["rule_id"] for i in inc}


# --- GuardDuty: GUARDDUTY-HIGH-01 ----------------------------------------
def test_guardduty_high_01_hit_ec2():
    inc = _run({"GuardDuty": {"fid-1": {"Severity": 8.0, "Type": "UnauthorizedAccess:EC2/MaliciousIPCaller", "ServiceName": "EC2", "CreatedAt": "", "UpdatedAt": ""}}})
    by = _by_rule(inc)
    assert "GUARDDUTY-HIGH-01" in by
    assert by["GUARDDUTY-HIGH-01"]["level"] == "CRITICAL"


def test_guardduty_high_01_hit_backdoor():
    inc = _run({"GuardDuty": {"fid-2": {"Severity": 9.0, "Type": "Backdoor:EC2", "ServiceName": "EC2", "CreatedAt": "", "UpdatedAt": ""}}})
    by = _by_rule(inc)
    assert "GUARDDUTY-HIGH-01" in by
    assert "HUMAN ESCALATION" in by["GUARDDUTY-HIGH-01"]["title"]


def test_guardduty_high_01_miss_low_severity():
    # Severity < 7
    inc = _run({"GuardDuty": {"fid-3": {"Severity": 5.0, "Type": "Trojan:EC2", "ServiceName": "EC2", "CreatedAt": "", "UpdatedAt": ""}}})
    assert "GUARDDUTY-HIGH-01" not in {i["rule_id"] for i in inc}


# --- SecurityHub: SECHUB-FAILED-01 ----------------------------------------
def test_sechub_failed_01_hit_warn():
    from datetime import datetime, timezone, timedelta
    past = datetime.now(timezone.utc) - timedelta(days=10)
    inc = _run({"SecurityHub": {"sh-1": {"ComplianceStatus": "FAILED", "WorkflowStatus": "NEW", "FirstObservedAt": past.isoformat(), "Title": "S3 bucket open", "ProductName": "Security Hub"}}})
    by = _by_rule(inc)
    assert "SECHUB-FAILED-01" in by
    assert by["SECHUB-FAILED-01"]["level"] == "WARNING"


def test_sechub_failed_01_hit_crit():
    from datetime import datetime, timezone, timedelta
    past = datetime.now(timezone.utc) - timedelta(days=35)
    inc = _run({"SecurityHub": {"sh-2": {"ComplianceStatus": "FAILED", "WorkflowStatus": "NEW", "FirstObservedAt": past.isoformat(), "Title": "S3 bucket open", "ProductName": "Security Hub"}}})
    by = _by_rule(inc)
    assert "SECHUB-FAILED-01" in by
    assert by["SECHUB-FAILED-01"]["level"] == "CRITICAL"


def test_sechub_failed_01_miss_resolved():
    from datetime import datetime, timezone, timedelta
    past = datetime.now(timezone.utc) - timedelta(days=10)
    inc = _run({"SecurityHub": {"sh-3": {"ComplianceStatus": "FAILED", "WorkflowStatus": "RESOLVED", "FirstObservedAt": past.isoformat(), "Title": "Old issue", "ProductName": "Security Hub"}}})
    assert "SECHUB-FAILED-01" not in {i["rule_id"] for i in inc}


def test_sechub_failed_01_miss_passed():
    inc = _run({"SecurityHub": {"sh-4": {"ComplianceStatus": "PASSED", "WorkflowStatus": "NEW", "FirstObservedAt": "", "Title": "All good", "ProductName": "Security Hub"}}})
    assert "SECHUB-FAILED-01" not in {i["rule_id"] for i in inc}
