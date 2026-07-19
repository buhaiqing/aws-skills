# Cost Tracking — Lambda per-Function Cost Analysis

_Last updated: 2026-07-19_

This document defines how to track Lambda cost using AWS Cost Explorer and CloudWatch.

---

## 1. Per-Resource Cost Query

### By Function Name (Tag)

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS Lambda"]}}' \
  --group-by '[{"Type":"TAG","Key":"FunctionName"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Metrics.BlendedCost.Amount`

### By Linked Account

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS Lambda"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Keys[]` (account IDs)

---

## 2. Idle Resource Detection

### Invocations = 0 for 30 Consecutive Days

**Criteria**: `Invocations = 0` for 30 days

```bash
# Step 1: List all Lambda functions
aws lambda list-functions \
  --output json \
  --query 'Functions[].[FunctionName,Runtime,MemorySize]'

# Step 2: Check invocations for each function over 30 days
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value={{user.function_name}} \
  --start-time 2026-06-19T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Sum
```

**JSON path**: `Datapoints[].Sum`

### Idle Function Detection Output

```json
{
  "function_name": "staging-data-processor",
  "runtime": "python3.11",
  "memory_mb": 512,
  "idle_days": 30,
  "total_invocations": 0,
  "estimated_monthly_cost": 2.00,
  "recommendation": "Delete or Disable"
}
```

---

## 3. Savings Recommendations

### Provisioned Concurrency Utilization

```bash
aws lambda get-provisioned-concurrency-config \
  --output json \
  --function-name "{{user.function_name}}" \
  --qualifier "{{user.qualifier}}"
```

**JSON path**: `AllocatedProvisionedConcurrentExecutions`

### Savings Plans Coverage

```bash
aws ce get-savings-plans-coverage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AWS Lambda"]}}'
```

### Lambda@Edge Cost Analysis

```bash
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=Region,Value=Global \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Sum
```

### Idle Lambda Savings Report

```json
{
  "total_idle_functions": 12,
  "estimated_monthly_savings": 24.00,
  "potential_annual_savings": 288.00
}
```

---

## 4. Anomaly Detection

### Request Volume Spike Detection (> 10x Baseline)

```bash
# Get baseline invocations
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value={{user.function_name}} \
  --start-time 2026-06-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Average
```

**JSON path**: `Datapoints[].Average`

### Duration Anomaly

```bash
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value={{user.function_name}} \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Anomaly Alert Output

```json
{
  "alert_type": "request_volume_spike",
  "function_name": "api-handler",
  "baseline_avg": 1000,
  "current_value": 15000,
  "increase_factor": 15,
  "additional_monthly_cost_estimate": 45.00,
  "status": "ALERT"
}
```
