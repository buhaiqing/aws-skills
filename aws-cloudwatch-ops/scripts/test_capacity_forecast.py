#!/usr/bin/env python3
"""Tests for capacity_forecast.py — predict_capacity() and batch_forecast()."""

import pytest
from capacity_forecast import (
    predict_capacity,
    batch_forecast,
    DEFAULT_WARNING,
    DEFAULT_CRITICAL,
)


# ─── predict_capacity() test cases ───────────────────────────────────────────

def test_normal_data_increasing_trend():
    """14 days of hourly data with a clear upward trend → predictable."""
    # Simulate CPU rising from 40% to 80% over 14 days
    data = [{"Average": round(40 + i * (40 / 336), 1)} for i in range(336)]
    result = predict_capacity(data)

    assert result["predictable"] is True
    assert result["data_points"] == 336
    assert result["trend"] == "increasing"
    assert result["confidence"] == "high"
    assert result["forecast_7d_avg"] is not None
    assert result["forecast_7d_max"] is not None
    assert result["current_avg"] < result["forecast_7d_avg"]
    # With this slope the 7d forecast should exceed warning (80%)
    assert result["will_exceed_warning"] is True


def test_insufficient_data():
    """Fewer than 2 data points → not predictable."""
    result = predict_capacity([])
    assert result["predictable"] is False
    assert result["reason"] == "insufficient_data"
    assert result["data_points"] == 0

    result = predict_capacity([{"Average": 50.0}])
    assert result["predictable"] is False
    assert result["reason"] == "insufficient_data"


def test_stable_trend():
    """Flat data (zero slope) → stable trend, no alert."""
    data = [{"Average": 55.0}] * 336
    result = predict_capacity(data)

    assert result["predictable"] is True
    assert result["trend"] == "stable"
    assert result["slope"] == 0.0
    assert result["alert_level"] == "OK"
    assert result["will_exceed_warning"] is False
    assert result["will_exceed_critical"] is False


def test_increasing_trend_with_no_exceed():
    """Slowly increasing trend below thresholds → OK."""
    # slope = 0.06 → increasing but max forecast ~60 < 80
    data = [{"Average": round(30.0 + i * 0.06, 1)} for i in range(336)]
    result = predict_capacity(data, warning_thresh=80, critical_thresh=90)

    assert result["predictable"] is True
    assert result["trend"] == "increasing"
    assert result["alert_level"] == "OK"
    assert result["will_exceed_warning"] is False
    assert result["will_exceed_critical"] is False


def test_decreasing_trend():
    """Downward trend → stable (slope magnitude below threshold)."""
    data = [{"Average": round(80 - i * (10 / 336), 1)} for i in range(336)]
    result = predict_capacity(data, warning_thresh=80, critical_thresh=90)

    assert result["predictable"] is True
    assert result["trend"] in ("decreasing", "stable")
    assert result["forecast_7d_avg"] < result["current_avg"]


def test_critical_alert_level():
    """High values → CRITICAL."""
    data = [{"Average": 92.0}] * 336
    result = predict_capacity(data, warning_thresh=80, critical_thresh=90)

    assert result["predictable"] is True
    assert result["alert_level"] == "CRITICAL"
    assert result["will_exceed_critical"] is True


def test_warning_alert_level():
    """Mid-range values → WARNING."""
    data = [{"Average": 83.0}] * 336
    result = predict_capacity(data, warning_thresh=80, critical_thresh=90)

    assert result["predictable"] is True
    assert result["alert_level"] == "WARNING"
    assert result["will_exceed_warning"] is True
    assert result["will_exceed_critical"] is False


def test_confidence_medium():
    """168 data points (7 days) → medium confidence."""
    data = [{"Average": 50.0 + i * 0.1} for i in range(168)]
    result = predict_capacity(data)
    assert result["confidence"] == "medium"


def test_confidence_low():
    """Less than 7 days of data → low confidence."""
    data = [{"Average": 50.0}] * 100
    result = predict_capacity(data)
    assert result["confidence"] == "low"


def test_clamp_to_100():
    """Predictions must not exceed 100."""
    # Extreme upward trend would overshoot 100
    data = [{"Average": round(95 + i * 2, 1)} for i in range(24)]
    result = predict_capacity(data, warning_thresh=80, critical_thresh=90)
    assert result["forecast_7d_max"] <= 100.0


def test_clamp_to_0():
    """Predictions must not go below 0."""
    data = [{"Average": round(5 - i * 0.1, 1)} for i in range(336)]
    result = predict_capacity(data)
    assert result["forecast_7d_avg"] >= 0.0
    assert result["forecast_7d_max"] >= 0.0


def test_recommendation_field_present():
    """predict_capacity adds alert_level for downstream use."""
    data = [{"Average": 85.0}] * 336
    result = predict_capacity(data)
    assert "alert_level" in result
    assert result["alert_level"] in ("OK", "WARNING", "CRITICAL")


# ─── batch_forecast() test cases ─────────────────────────────────────────────

def test_batch_forecast_multiple_resources():
    """batch_forecast returns one result per resource."""
    resources = [
        {
            "resource_id": "i-abc123",
            "namespace": "AWS/EC2",
            "metric": "CPUUtilization",
            "metric_data": [{"Average": 70.0}] * 336,
            "forecast_days": 7,
        },
        {
            "resource_id": "i-xyz789",
            "namespace": "AWS/EC2",
            "metric": "CPUUtilization",
            "metric_data": [{"Average": 30.0}] * 336,
            "forecast_days": 7,
        },
    ]
    results = batch_forecast(resources, warning_thresh=80, critical_thresh=90)
    assert len(results) == 2
    assert results[0]["resource_id"] == "i-abc123"
    assert results[1]["resource_id"] == "i-xyz789"
    assert all(r["predictable"] for r in results)


def test_batch_forecast_per_resource_override():
    """Per-resource threshold overrides respected."""
    resources = [
        {
            "resource_id": "rds-1",
            "namespace": "AWS/RDS",
            "metric": "DatabaseConnections",
            "metric_data": [{"Average": 50.0}] * 336,
            "warning_thresh": 60,
            "critical_thresh": 80,
        },
    ]
    results = batch_forecast(resources,
                             warning_thresh=DEFAULT_WARNING,
                             critical_thresh=DEFAULT_CRITICAL)
    assert results[0]["warning_thresh"] == 60
    assert results[0]["critical_thresh"] == 80


def test_batch_forecast_empty_list():
    """Empty resource list → empty results."""
    results = batch_forecast([])
    assert results == []
