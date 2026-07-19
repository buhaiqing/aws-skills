# Anomaly Detection Logic

## 7-Day Baseline Calculation

1. Query DAILY cost for each service for the past 7 days
2. Compute average daily cost per service
3. Compare today's cost to baseline average

```bash
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output json
```

## Anomaly Thresholds

| Level | Condition | Action |
|---|---|---|
| WARNING | `cost > baseline × {{user.threshold_pct}} / 100` | Log to report |
| CRITICAL | `cost > baseline × 1.5` | Flag for immediate review |

Default `threshold_pct = 130` (WARNING at 130% of 7-day avg).

## Pseudocode

```
baseline = sum(daily_costs[day-7 to day-1]) / 7
today_cost = daily_costs[day]
ratio = today_cost / baseline

if ratio > 1.5: severity = CRITICAL
elif ratio > threshold_pct / 100: severity = WARNING
else: severity = OK
```

## Common JSON Paths

```python
# get-cost-and-usage response
$.ResultsByTime[].TimePeriod.Start
$.ResultsByTime[].Groups[].Keys[0]  # service name
$.ResultsByTime[].Groups[].Metrics.BlendedCost.Amount
```
