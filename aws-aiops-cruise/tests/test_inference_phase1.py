#!/usr/bin/env python3
"""Unit tests for Phase-1 inference rules (DynamoDB / ElastiCache / OpenSearch).

Verifies the rule blocks added to `apply_chain_inference` in
`runbooks/scripts/_inference.py`:
  DYNAMO-THROTTLE-01, DYNAMO-GSI-01, EC-MEM-01, EC-FAILOVER-01,
  OS-HEAP-01, OS-SHARD-01
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _inference import apply_chain_inference  # noqa: E402


def _phase1_signals() -> dict:
    return {
        "DynamoDB": {
            "tbl-1": {"ThrottledRequests": 5, "GSIWriteThrottleEvents": 0},
            "tbl-2": {"ThrottledRequests": 0, "GSIWriteThrottleEvents": 12},
        },
        "ElastiCache": {
            "cache-1": {"DatabaseMemoryUsagePercentage": 90, "FailoverInProgress": 0},
            "cache-2": {"DatabaseMemoryUsagePercentage": 70, "FailoverInProgress": 1},
        },
        "OpenSearch": {
            "os-1": {"JVMMemoryPressure": 85, "ClusterIndexWritesBlocked": 0, "UnassignedShards": 0},
            "os-2": {"JVMMemoryPressure": 60, "ClusterIndexWritesBlocked": 1, "UnassignedShards": 0},
            "os-3": {"JVMMemoryPressure": 60, "ClusterIndexWritesBlocked": 0, "UnassignedShards": 3},
        },
    }


def test_phase1_rules_fire():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    ids = {i["rule_id"] for i in inc}
    assert "DYNAMO-THROTTLE-01" in ids
    assert "DYNAMO-GSI-01" in ids
    assert "EC-MEM-01" in ids
    assert "EC-FAILOVER-01" in ids
    assert "OS-HEAP-01" in ids
    assert "OS-SHARD-01" in ids
    assert len(lines) >= 6


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
    assert by_id["OS-HEAP-01"]["level"] == "WARNING"
    # OS-SHARD-01 fires for both os-2 (writes blocked -> CRITICAL) and
    # os-3 (unassigned shards -> WARNING); collect all levels per rule.
    shard_levels = [i["level"] for i in inc if i["rule_id"] == "OS-SHARD-01"]
    assert "CRITICAL" in shard_levels
    assert "WARNING" in shard_levels


def test_phase1_suppressed_by_existing_rule_ids():
    inc, lines = apply_chain_inference(
        _phase1_signals(), run_id="r1", customer="c", region="us-east-1",
        existing_rule_ids={
            "DYNAMO-THROTTLE-01", "DYNAMO-GSI-01", "EC-MEM-01",
            "EC-FAILOVER-01", "OS-HEAP-01", "OS-SHARD-01",
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
        "OpenSearch": {"os-1": {"JVMMemoryPressure": 30, "ClusterIndexWritesBlocked": 0, "UnassignedShards": 0}},
    }
    inc, _ = apply_chain_inference(
        clean, run_id="r1", customer="c", region="us-east-1", existing_rule_ids=set()
    )
    assert inc == []
