# Cost Explorer API Reference

All commands use `--output json` and standard `aws ce <op>` form.

## Common JSON Paths

```python
# Cost and Usage by Service
$.ResultsByTime[].Groups[].Keys[]
$.ResultsByTime[].Groups[].Metrics.BlendedCost.Amount
$.ResultsByTime[].Groups[].Metrics.BlendedCost.Unit

# Cost Forecast
$.ForecastResultsByTime[].MeanForecastValue
$.ForecastResultsByTime[].PredictionIntervalUpperBound
$.ForecastResultsByTime[].PredictionIntervalLowerBound

# Reservation Coverage
$.Coverages[].CoverageCoverageHours.NormalizedUnits
$.Coverages[].CoverageCoverageHours.CoverageHoursPercentage

# Savings Plans Coverage
$.SavingsPlansCoverages[].Coverage.SpendCoveredBySavingsPlans.Percentage
```

## get-cost-and-usage

Daily cost by service:

```bash
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity DAILY \
  --metrics BlendedCost UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output json
```

By tag:

```bash
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Environment \
  --filter '{"Tags":{"Key":"Environment","Values":["prod","staging","dev"]}}' \
  --output json
```

Monthly summary:

```bash
aws ce get-cost-and-usage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity MONTHLY \
  --metrics BlendedCost UnblendedCost UsageQuantity \
  --output json
```

## get-cost-forecast

```bash
aws ce get-cost-forecast \
  --time-period Start={{start_date}},End={{end_date}} \
  --metric BLENDED_COST \
  --prediction-interval-level 95 \
  --output json
```

## get-reservation-coverage

```bash
aws cost-explorer get-reservation-coverage \
  --time-period Start={{start_date}},End={{end_date}} \
  --metrics CoverageHours NormalizedUnitsAverageUtilization \
  --granularity DAILY \
  --output json
```

## get-savings-plans-coverage

```bash
aws ce get-savings-plans-coverage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity DAILY \
  --output json
```

## get-dimension-values (for filter construction)

```bash
aws ce get-dimension-values \
  --time-period Start={{start_date}},End={{end_date}} \
  --dimension LINKED_ACCOUNT \
  --output json
```
