# Capacity Alert Thresholds

> Configurable threshold parameters for capacity forecasting. Values are adjustable per deployment context.

## Default Thresholds

| Parameter | Default Value | Unit | Description |
|-----------|---------------|------|-------------|
| `warning_threshold` | 80 | % | Forecast exceeds this → WARNING level |
| `critical_threshold` | 90 | % | Forecast exceeds this → CRITICAL level |
| `min_history_days` | 14 | days | Minimum historical data for prediction |
| `forecast_days` | 7 | days | Default forecast horizon |

## Per-Rule Threshold Overrides

Override defaults in `capacity_forecast.py` calls:

```python
from scripts.capacity_forecast import batch_forecast

# EC2: stricter thresholds for production
results = batch_forecast(resources,
    warning_thresh=70,
    critical_thresh=85)

# RDS: use connection-based thresholds
results = batch_forecast(rds_resources,
    warning_thresh=80,
    critical_thresh=95,
    threshold_mode="connections")  # relative to max_connections
```

## Threshold Modes

| Mode | Description | Applicable Metrics |
|------|-------------|-------------------|
| `percent` (default) | Raw percentage 0–100 | CPUUtilization, MemoryUsage |
| `connections` | % of `max_connections` | RDS DatabaseConnections |
| `capacity` | % of known connection limit | ALB ActiveConnectionCount |

## Adjustment Guidelines

- **Development/ staging**: warning=85, critical=95
- **Production**: warning=70–80, critical=85–90
- **Cost-optimized**: warning=60, critical=80 (trigger earlier downsize)

## YAML Configuration

```yaml
# assets/capacity-thresholds.yaml
defaults:
  warning_threshold: 80
  critical_threshold: 90
  min_history_days: 14
  forecast_days: 7
  confidence_min_data_points: 168  # 7 days × 24h

overrides:
  - rule: CAP-FC-01  # EC2
    warning_threshold: 70
    critical_threshold: 85
  - rule: CAP-FC-03  # RDS
    threshold_mode: connections
    warning_threshold: 80
    critical_threshold: 95
```

## Clamping

Forecast values are always clamped to `[0, 100]` regardless of input data range.
