#!/usr/bin/env python3
"""Unit tests for Phase-1 inference rules (DynamoDB GSI / ElastiCache failover).

Verifies the rule blocks added to `apply_chain_inference` in
`runbooks/scripts/_inference.py` for the Level-3 coverage-gap closure:
  DYNAMO-GSI-01, EC-FAILOVER-01

Note: OpenSearch / CloudFront / EKS / Athena / RAM / SecretsManager inference
rules are DEFERRED — `signals["<svc>"]` is never populated because those
services have no PRODUCTS entry in `_shared.py`, so inference blocks would be
dead code. Their routing is wired in cruise/orchestrator SKILL.md; inference
follows once a metrics collector exists. See
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
