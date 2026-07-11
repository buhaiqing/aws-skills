#!/usr/bin/env python3
"""Unit tests for Phase-1 inference rules (DynamoDB GSI / ElastiCache failover).

Verifies the rule blocks added to `apply_chain_inference` in
`runbooks/scripts/_inference.py` for the Level-3 coverage-gap closure:
  DYNAMO-GSI-01, EC-FAILOVER-01

Note: OpenSearch / CloudFront / Athena / RAM / SecretsManager inference rules
remain DEFERRED — `signals["<svc>"]` is never populated because those services
have no PRODUCTS entry in `_shared.py`, so inference blocks would be dead code.
EKS is the exception: `audit_eks_nodes` (native collector) populates
`signals["EKS"]` at runtime, so `EKS-NG-02` fires; the EKS_NODE layer
(CloudWatch Container Insights) drives `EKS-NODE-01` / `EKS-OOM-01`. See
`references/inference-rules-addendum.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _inference import apply_chain_inference  # noqa: E402


def _phase1_signals() -> dict:
    # Only resource types with a PRODUCTS entry in _shared.py reach
    # _inference.py in production. DynamoDB + ElastiCache both qualify.
    return {
        "DynamoDB": {
            "tbl-1": {"ThrottledRequests": 5, "GSIWriteThrottleEvents": 0},
            "tbl-2": {"ThrottledRequests": 0, "GSIWriteThrottleEvents": 12},
        },
        "ElastiCache": {
            "cache-1": {"DatabaseMemoryUsagePercentage": 90, "FailoverInProgress": 0},
            "cache-2": {"DatabaseMemoryUsagePercentage": 70, "FailoverInProgress": 1},
        },
        "EKS": {
            "prod/my-ng": {"NodesDesired": 4.0, "NodesCurrent": 2.0, "NodesMin": 2.0, "NodesMax": 6.0},
            "prod/full-ng": {"NodesDesired": 6.0, "NodesCurrent": 6.0, "NodesMin": 2.0, "NodesMax": 6.0},
            "prod/ok-ng": {"NodesDesired": 3.0, "NodesCurrent": 3.0, "NodesMin": 2.0, "NodesMax": 6.0},
        },
    }


def test_phase1_new_rules_fire():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    ids = {i["rule_id"] for i in inc}
    assert "DYNAMO-GSI-01" in ids
    assert "EC-FAILOVER-01" in ids
    assert len(lines) >= 2


def test_phase1_levels():
    inc, _ = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    by_id = {i["rule_id"]: i for i in inc}
    # throttle <10 -> WARNING; GSI >=10 -> CRITICAL
    assert by_id["DYNAMO-THROTTLE-01"]["level"] == "WARNING"
    assert by_id["DYNAMO-GSI-01"]["level"] == "CRITICAL"
    # EC mem 90 -> WARNING (threshold 80/95)
    assert by_id["EC-MEM-01"]["level"] == "WARNING"
    assert by_id["EC-FAILOVER-01"]["level"] == "CRITICAL"


def test_phase1_suppressed_by_existing_rule_ids():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1",
        existing_rule_ids={
            "DYNAMO-THROTTLE-01", "DYNAMO-GSI-01", "EC-MEM-01", "EC-FAILOVER-01",
            "EKS-NG-02",
        },
    )
    assert inc == []
    assert lines == []


def test_phase1_no_signal_no_incident():
    inc, _ = apply_chain_inference(
        {}, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    assert inc == []


def test_phase1_no_false_positive_on_clean_signal():
    clean = {
        "DynamoDB": {"tbl-1": {"ThrottledRequests": 0, "GSIWriteThrottleEvents": 0}},
        "ElastiCache": {"cache-1": {"DatabaseMemoryUsagePercentage": 40, "FailoverInProgress": 0}},
    }
    inc, _ = apply_chain_inference(
        clean, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    assert inc == []


def test_eks_ng02_fires_with_levels():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    eks = [i for i in inc if i["rule_id"] == "EKS-NG-02"]
    assert len(eks) == 2  # my-ng (under-scaled) + full-ng (at max), ok-ng clean
    by_id = {i["resource_id"]: i for i in eks}
    assert by_id["prod/my-ng"]["level"] == "CRITICAL"
    assert by_id["prod/full-ng"]["level"] == "WARNING"
    assert len(lines) >= 2


def test_eks_ng02_suppressed_by_existing_rule_ids():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1",
        existing_rule_ids={"EKS-NG-02"},
    )
    assert [i for i in inc if i["rule_id"] == "EKS-NG-02"] == []
    assert all("EKS-NG-02" not in ln for ln in lines)


def test_eks_ng02_no_false_positive_on_clean_signal():
    clean = {"EKS": {"prod/ok-ng": {"NodesDesired": 3.0, "NodesCurrent": 3.0, "NodesMin": 2.0, "NodesMax": 6.0}}}
    inc, _ = apply_chain_inference(
        clean, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    assert [i for i in inc if i["rule_id"] == "EKS-NG-02"] == []


def _eks_node_signals() -> dict:
    # signals["EKS_NODE"] is populated by the Container Insights collector
    # (compute.py audit_eks_nodes), keyed by cluster name.
    return {
        "EKS_NODE": {
            "prod/cluster-1": {"NodeNotReadyMin": 0.5, "PodOOMKilledSum": 3.0},
            "prod/cluster-2": {"NodeNotReadyMin": 3.0, "PodOOMKilledSum": 0.0},
        },
    }


def test_eks_node_01_and_oom_01_fire():
    inc, lines = apply_chain_inference(
        _eks_node_signals(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    by_rule = {i["rule_id"]: i for i in inc}
    assert "EKS-NODE-01" in by_rule
    assert "EKS-OOM-01" in by_rule
    # node NotReady -> WARNING; pod OOM -> CRITICAL
    assert by_rule["EKS-NODE-01"]["level"] == "WARNING"
    assert by_rule["EKS-OOM-01"]["level"] == "CRITICAL"
    # only cluster-1 is unhealthy; cluster-2 must not raise either rule
    assert by_rule["EKS-NODE-01"]["resource_id"] == "prod/cluster-1"
    assert by_rule["EKS-OOM-01"]["resource_id"] == "prod/cluster-1"
    assert len(lines) >= 2


def test_eks_node_rules_suppressed_by_existing_rule_ids():
    inc, lines = apply_chain_inference(
        _eks_node_signals(), run_id="r1", customer="c", region="us-east-1",
        existing_rule_ids={"EKS-NODE-01", "EKS-OOM-01"},
    )
    assert [i for i in inc if i["rule_id"] in ("EKS-NODE-01", "EKS-OOM-01")] == []
    assert all("EKS-NODE-01" not in ln and "EKS-OOM-01" not in ln for ln in lines)


def test_eks_node_clean_no_false_positive():
    inc, _ = apply_chain_inference(
        {}, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    assert [i for i in inc if i["rule_id"] in ("EKS-NODE-01", "EKS-OOM-01")] == []
