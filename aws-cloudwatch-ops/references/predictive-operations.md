# Predictive Operations

Predictive operations use CloudWatch metrics and forecasts to anticipate capacity issues before they occur.

## get-capacity-forecast

Predict capacity utilization based on 14-day historical trend. Used by `aws-aiops-cruise` for proactive resize recommendations.

### Pre-flight

Collect 14-day history via `get_metric_statistics`, then invoke `scripts/capacity_forecast.py`:

```bash
aws cloudwatch get-metric-statistics \
  --namespace "{{user.ns}}" \
  --metric-name "{{user.metric}}" \
  --statistics Average \
  --period 3600 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region "{{user.region}}" --output json
```

### Execute — Python (capacity_forecast.py)

```python
from scripts.capacity_forecast import batch_forecast
results = batch_forecast([{"resource_id": "{{user.resource_id}}",
  "namespace": "{{user.ns}}", "metric": "{{user.metric}}",
  "period": 3600, "forecast_days": {{user.forecast_days|7}}}],
  warning_thresh=80, critical_thresh=90)
```

### Output Schema

```json
{
  "capacity_forecast": {
    "resource_id": "{{user.resource_id}}",
    "metric": "{{user.metric}}",
    "current_avg": 65.5,
    "forecast_7d_avg": 78.3,
    "forecast_7d_max": 92.1,
    "trend": "increasing|stable|decreasing",
    "alert_level": "OK|WARNING|CRITICAL",
    "recommendation": "Proactive resize ...",
    "confidence": "high|medium|low",
    "data_points_analyzed": 336
  }
}
```

### Validate

Confirm `alert_level` is set and `forecast_7d_avg` is populated. Refs: `references/capacity-forecast-rules.md`, `references/capacity-alert-thresholds.md`.

## FORECAST Metric Trend

Use CloudWatch metric math `FORECAST()` for linear trend prediction.

### Pre-flight

Ensure sufficient historical data (≥14 days recommended).

### Execute — CLI (Primary)

```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{user.ns}}","MetricName":"{{user.metric}}"},"Stat":"Average","Period":3600}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)", "Label":"7-Day Forecast"}
  ]' \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region "{{user.region}}" \
  --output json
```

### Execute — boto3 (Fallback)

```python
response = client.get_metric_data(
    MetricDataQueries=[
        {'Id': 'm1', 'MetricStat': {'Metric': {'Namespace': '{{user.ns}}', 'MetricName': '{{user.metric}}'}, 'Stat': 'Average', 'Period': 3600}},
        {'Id': 'fc', 'Expression': 'FORECAST(m1, "linear", 168)', 'Label': '7-Day Forecast'}
    ],
    StartTime=datetime.utcnow() - timedelta(days=14),
    EndTime=datetime.utcnow()
)
```

### Validate

Check `.MetricDataResults[]` contains both actual and forecast results.

### Recover

| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix forecast model/period; retry once |
| ThrottlingException | Backoff; retry 3x |
