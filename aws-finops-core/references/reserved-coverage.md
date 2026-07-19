# Reserved Instance & Savings Plans Coverage

## Query RI Coverage

```bash
aws cost-explorer get-reservation-coverage \
  --time-period Start={{start_date}},End={{end_date}} \
  --metrics CoverageHours CoverageNormalizedUnitsAverageUtilization \
  --granularity MONTHLY \
  --output json
```

## Query SP Coverage

```bash
aws ce get-savings-plans-coverage \
  --time-period Start={{start_date}},End={{end_date}} \
  --granularity MONTHLY \
  --output json
```

## Optimization Thresholds

| Metric | < 70% Coverage | 70–85% | > 85% |
|---|---|---|---|
| RI Coverage | Purchase more RIs | Review utilization | Optimal |
| SP Coverage | Consider SPs | Review blend | Optimal |

Low utilization (< 50%) suggests oversized reservations.

## Common JSON Paths

```python
# RI Coverage
$.Coverages[].CoverageCoverageHours.CoverageHoursPercentage
$.Coverages[].CoverageCoverageHours.NormalizedUnitsAverageUtilization

# SP Coverage
$.SavingsPlansCoverages[].Coverage.SpendCoveredBySavingsPlans.Percentage
$.SavingsPlansCoverages[].Coverage.OnDemandCost
```
