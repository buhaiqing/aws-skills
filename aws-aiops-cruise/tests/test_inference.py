#!/usr/bin/env python3
"""Unit tests for inference helpers (V1) and percentile wiring (V2)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "runbooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pytest  # noqa: E402

from _inference import (  # noqa: E402
    extract_xray_latency_signals,
    build_inference_latency_table,
    infer_latency_p95_rule,
)
from _shared import percentile_from_buckets  # noqa: E402


# ---------------------------------------------------------------------------
# V1: percentile_from_buckets
# ---------------------------------------------------------------------------
class TestPercentileFromBuckets:
    """Spec §S1 (ID-2, ID-3)."""

    def test_empty_returns_none(self):
        assert percentile_from_buckets([], 0.95) is None
        assert percentile_from_buckets(None, 0.95) is None

    def test_invalid_p_returns_none(self):
        buckets = [{"Key": "1.0", "Value": 10}]
        assert percentile_from_buckets(buckets, 0) is None
        assert percentile_from_buckets(buckets, -0.5) is None
        assert percentile_from_buckets(buckets, 1.1) is None

    def test_zero_total_count_returns_none(self):
        buckets = [{"Key": "0.1", "Value": 0}, {"Key": "1.0", "Value": 0}]
        assert percentile_from_buckets(buckets, 0.95) is None

    def test_single_bucket(self):
        # All 100 samples in [0, 0.5s] (bucket upper bound = 0.5).
        # Linear interpolation: rank = p*100, frac = rank/100, value = 0 + 0.5*frac.
        buckets = [{"Key": "0.5", "Value": 100}]
        assert percentile_from_buckets(buckets, 0.5) == 0.25
        assert percentile_from_buckets(buckets, 0.95) == pytest.approx(0.475, rel=0.01)
        assert percentile_from_buckets(buckets, 0.99) == pytest.approx(0.495, rel=0.01)

    def test_three_bucket_p50(self):
        # 100 samples split evenly: 33 in [0,0.1], 33 in [0.1,0.5], 34 in [0.5,1.0]
        # P50 rank = 50 → falls in 2nd bucket, interpolated:
        # frac = (50-33)/33 ≈ 0.515; value = 0.1 + (0.5-0.1)*0.515 ≈ 0.306
        buckets = [
            {"Key": "0.1", "Value": 33},
            {"Key": "0.5", "Value": 33},
            {"Key": "1.0", "Value": 34},
        ]
        p50 = percentile_from_buckets(buckets, 0.5)
        assert p50 is not None
        assert 0.28 <= p50 <= 0.32, f"p50={p50} out of expected band"

    def test_three_bucket_p95(self):
        # P95 rank = 95 → falls in 3rd bucket:
        # frac = (95-66)/34 ≈ 0.853; value = 0.5 + (1.0-0.5)*0.853 ≈ 0.926
        buckets = [
            {"Key": "0.1", "Value": 33},
            {"Key": "0.5", "Value": 33},
            {"Key": "1.0", "Value": 34},
        ]
        p95 = percentile_from_buckets(buckets, 0.95)
        assert p95 is not None
        assert 0.90 <= p95 <= 0.95, f"p95={p95} out of expected band"

    def test_three_bucket_p99(self):
        # P99 rank = 99 → 3rd bucket, frac = (99-66)/34 ≈ 0.971; value ≈ 0.985
        buckets = [
            {"Key": "0.1", "Value": 33},
            {"Key": "0.5", "Value": 33},
            {"Key": "1.0", "Value": 34},
        ]
        p99 = percentile_from_buckets(buckets, 0.99)
        assert p99 is not None
        assert 0.97 <= p99 <= 1.0, f"p99={p99} out of expected band"

    def test_malformed_buckets_skipped(self):
        buckets = [
            {"Key": "not-a-number", "Value": 10},
            {"Key": "1.0", "Value": "bad-count"},
            {"Key": "2.0", "Value": 5},
        ]
        # Only the last valid bucket contributes; total=5, p50=2.5 → frac=0.5 → value=1.0
        assert percentile_from_buckets(buckets, 0.5) == pytest.approx(1.0, rel=0.01)

    def test_unsorted_buckets_handled(self):
        # X-Ray API may return unsorted; must sort internally
        buckets = [
            {"Key": "1.0", "Value": 50},
            {"Key": "0.1", "Value": 50},
        ]
        p95 = percentile_from_buckets(buckets, 0.95)
        # rank = 95, cumulative: 50 in [0,0.1] then 50 in [0.1,1.0] → frac = 45/50 = 0.9
        # value = 0.1 + (1.0-0.1)*0.9 = 0.91
        assert p95 is not None
        assert 0.85 <= p95 <= 0.95, f"p95={p95} out of expected band"


# ---------------------------------------------------------------------------
# V2: extract_xray_latency_signals
# ---------------------------------------------------------------------------
class TestExtractXrayLatencySignals:
    """Spec §S1 — convert X-Ray service graph to percentile signals."""

    def test_empty_data(self):
        result = extract_xray_latency_signals(None)
        assert result == {}

    def test_no_services(self):
        result = extract_xray_latency_signals({})
        assert result == {}

    def test_service_with_response_time_histogram(self):
        # Synthetic X-Ray service with EdgeStatistics-style response time
        # (we use the same histogram shape for ResponseTime distribution)
        buckets = [
            {"Key": "0.1", "Value": 50},
            {"Key": "0.5", "Value": 30},
            {"Key": "1.0", "Value": 15},
            {"Key": "2.0", "Value": 5},
        ]
        # Real X-Ray shape: SummaryStatistics has TotalCount; per-edge histograms
        # live under EdgeStatistics (response time). Some AWS SDK versions return
        # the histogram at the service level. We accept both.
        data = {
            "Services": [
                {
                    "Name": "sagemaker-prod-endpoint",
                    "SummaryStatistics": {"TotalCount": 100, "FaultCount": 1, "ErrorCount": 0},
                    "EdgeStatistics": [
                        {
                            "ResponseTimeHistogram": buckets,
                        }
                    ],
                }
            ]
        }
        result = extract_xray_latency_signals(data)
        assert "sagemaker-prod-endpoint" in result
        sig = result["sagemaker-prod-endpoint"]
        assert "p50" in sig and "p95" in sig and "p99" in sig
        # All values in milliseconds
        assert sig["p50"] is not None and sig["p50"] > 0
        assert sig["p95"] is not None and sig["p95"] > sig["p50"]
        assert sig["p99"] is not None and sig["p99"] > sig["p95"]
        # Verify monotonic ordering at the millisecond level (X-Ray returns seconds)
        assert sig["p50"] < sig["p95"] < sig["p99"]

    def test_service_with_zero_total_count(self):
        data = {
            "Services": [
                {
                    "Name": "idle-service",
                    "SummaryStatistics": {"TotalCount": 0},
                }
            ]
        }
        result = extract_xray_latency_signals(data)
        # Service present but no percentiles (insufficient data)
        sig = result.get("idle-service", {})
        assert sig.get("p50") is None
        assert sig.get("n", 0) == 0


# ---------------------------------------------------------------------------
# V3: infer_latency_p95_rule
# ---------------------------------------------------------------------------
class TestInferLatencyP95Rule:
    """Spec §S2 — INFER-LAT-P95-01 rule emission."""

    def test_p95_below_sla_no_incident(self, monkeypatch):
        monkeypatch.setenv("INFER_P95_SLA_MS", "1500")
        signals = {
            "XRay": {
                "sagemaker-endpoint": {"p50": 100, "p95": 800, "p99": 1200, "n": 500}
            }
        }
        result = infer_latency_p95_rule(
            signals, run_id="test-run", customer="test-cust", region="us-east-1"
        )
        assert result == []

    def test_p95_in_warning_band(self, monkeypatch):
        monkeypatch.setenv("INFER_P95_SLA_MS", "1500")
        # p95 = 1700ms → 1.13× SLA → WARNING
        signals = {
            "XRay": {
                "sagemaker-endpoint": {"p50": 200, "p95": 1700, "p99": 2100, "n": 200}
            }
        }
        result = infer_latency_p95_rule(
            signals, run_id="test-run", customer="test-cust", region="us-east-1"
        )
        assert len(result) == 1
        assert result[0]["rule_id"] == "INFER-LAT-P95-01"
        assert result[0]["level"] == "WARNING"
        assert result[0]["resource_id"] == "sagemaker-endpoint"
        assert result[0]["metric"] == "P95LatencyMs"
        assert result[0]["threshold_warning"] == 1500
        assert result[0]["threshold_critical"] == 2250

    def test_p95_in_critical_band(self, monkeypatch):
        monkeypatch.setenv("INFER_P95_SLA_MS", "1500")
        # p95 = 2500ms → 1.67× SLA → CRITICAL
        signals = {
            "XRay": {
                "llm-endpoint": {"p50": 500, "p95": 2500, "p99": 4000, "n": 100}
            }
        }
        result = infer_latency_p95_rule(
            signals, run_id="test-run", customer="test-cust", region="us-east-1"
        )
        assert len(result) == 1
        assert result[0]["level"] == "CRITICAL"

    def test_empty_signals(self, monkeypatch):
        monkeypatch.setenv("INFER_P95_SLA_MS", "1500")
        result = infer_latency_p95_rule(
            {}, run_id="test-run", customer="test-cust", region="us-east-1"
        )
        assert result == []

    def test_sla_overridable_via_env(self, monkeypatch):
        monkeypatch.setenv("INFER_P95_SLA_MS", "500")
        # p95 = 600ms → 1.2× custom SLA → WARNING
        signals = {
            "XRay": {
                "fast-endpoint": {"p50": 50, "p95": 600, "p99": 800, "n": 50}
            }
        }
        result = infer_latency_p95_rule(
            signals, run_id="test-run", customer="test-cust", region="us-east-1"
        )
        assert len(result) == 1
        assert result[0]["threshold_warning"] == 500
        assert result[0]["threshold_critical"] == 750


# ---------------------------------------------------------------------------
# V4: build_inference_latency_table
# ---------------------------------------------------------------------------
class TestBuildInferenceLatencyTable:
    """Spec §S3 — Markdown table renderer."""

    def test_empty_signals(self):
        md = build_inference_latency_table({}, sla_ms=1500)
        assert "No inference endpoints detected" in md

    def test_single_endpoint_pass(self):
        signals = {
            "XRay": {
                "sagemaker-fast": {"p50": 100, "p95": 800, "p99": 1200, "n": 500}
            }
        }
        md = build_inference_latency_table(signals, sla_ms=1500)
        assert "sagemaker-fast" in md
        assert "1500ms" in md
        assert "✅" in md or "PASS" in md

    def test_single_endpoint_critical(self):
        signals = {
            "XRay": {
                "llm-slow": {"p50": 500, "p95": 2500, "p99": 4000, "n": 100}
            }
        }
        md = build_inference_latency_table(signals, sla_ms=1500)
        assert "llm-slow" in md
        assert "🔴" in md or "CRITICAL" in md
