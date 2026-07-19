#!/usr/bin/env python3
"""Capacity forecast — linear regression trend prediction on CloudWatch metrics."""

import statistics
from typing import Any

# ponytail: global defaults, per-call override in batch_forecast
DEFAULT_WARNING = 80.0
DEFAULT_CRITICAL = 90.0
DEFAULT_FORECAST_DAYS = 7


def predict_capacity(
    metric_data: list[dict[str, Any]],
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    warning_thresh: float = DEFAULT_WARNING,
    critical_thresh: float = DEFAULT_CRITICAL,
) -> dict[str, Any]:
    """
    Predict future capacity from CloudWatch get_metric_statistics datapoints.

    Args:
        metric_data: datapoints from AWS CW get_metric_statistics (list of dicts
                     with 'Average' key, e.g. [{'Average': 65.4}, ...])
        forecast_days: number of days to forecast
        warning_thresh: WARNING threshold percentage
        critical_thresh: CRITICAL threshold percentage

    Returns:
        dict with predictable, current_avg, forecast_7d_avg, forecast_7d_max,
        trend, will_exceed_warning, will_exceed_critical, confidence, data_points
    """
    values = [float(p["Average"]) for p in metric_data if "Average" in p]

    if len(values) < 2:
        return {
            "predictable": False,
            "reason": "insufficient_data",
            "data_points": len(values),
            "current_avg": None,
            "forecast_7d_avg": None,
            "forecast_7d_max": None,
            "trend": None,
            "will_exceed_warning": False,
            "will_exceed_critical": False,
            "confidence": None,
        }

    n = len(values)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(values) / n

    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
    den = sum((x - x_mean) ** 2 for x in x_vals)
    slope = num / den if den != 0 else 0.0
    intercept = y_mean - slope * x_mean

    # Forecast next `forecast_days` days (assuming hourly data → forecast_days * 24 steps)
    steps = forecast_days * 24
    predictions = []
    for i in range(1, steps + 1):
        predicted = intercept + slope * (n + i - 1)
        predictions.append(max(0.0, min(100.0, predicted)))  # clamp [0, 100]

    avg_prediction = statistics.mean(predictions)
    max_prediction = max(predictions)

    # Trend classification — absolute slope per data-point (hourly index)
    # ponytail: 0.05 per step ≈ 5% increase over 24h for typical %-metrics
    if slope > 0.05:
        trend = "increasing"
    elif slope < -0.05:
        trend = "decreasing"
    else:
        trend = "stable"

    # Alert levels
    alert_level = "OK"
    if avg_prediction >= critical_thresh:
        alert_level = "CRITICAL"
    elif avg_prediction >= warning_thresh:
        alert_level = "WARNING"

    # Confidence based on data points
    if n >= 336:  # 14 days × 24h
        confidence = "high"
    elif n >= 168:  # 7 days × 24h
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "predictable": True,
        "data_points": n,
        "current_avg": round(y_mean, 2),
        "forecast_7d_avg": round(avg_prediction, 2),
        "forecast_7d_max": round(max_prediction, 2),
        "trend": trend,
        "slope": round(slope, 4),
        "will_exceed_warning": any(p > warning_thresh for p in predictions),
        "will_exceed_critical": any(p > critical_thresh for p in predictions),
        "alert_level": alert_level,
        "confidence": confidence,
        "warning_thresh": warning_thresh,
        "critical_thresh": critical_thresh,
    }


def batch_forecast(
    resources: list[dict[str, Any]],
    warning_thresh: float = DEFAULT_WARNING,
    critical_thresh: float = DEFAULT_CRITICAL,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
) -> list[dict[str, Any]]:
    """
    Batch-forecast multiple resources.

    Args:
        resources: list of dicts with keys:
                  resource_id, namespace, metric, period (int),
                  and optionally forecast_days / warning_thresh / critical_thresh
        warning_thresh: default warning threshold
        critical_thresh: default critical threshold
        forecast_days: default forecast horizon

    Returns:
        list of dicts — one per resource, merged with predict_capacity output
    """
    results = []
    for r in resources:
        metric_data = r.get("metric_data", [])
        fw = r.get("warning_thresh", warning_thresh)
        fc = r.get("critical_thresh", critical_thresh)
        fd = r.get("forecast_days", forecast_days)
        pred = predict_capacity(metric_data, forecast_days=fd,
                                warning_thresh=fw, critical_thresh=fc)
        results.append({**r, **pred})
    return results


if __name__ == "__main__":
    import json, sys

    # Demo with synthetic data
    demo_data = [
        {"Average": round(50 + i * 0.5 + 2 * ((i % 7) - 3), 1)}
        for i in range(336)  # 14 days × 24h
    ]
    result = predict_capacity(demo_data)
    print(json.dumps(result, indent=2))
    sys.exit(0)
