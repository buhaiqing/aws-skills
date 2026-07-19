# Cost Tracking — EC2 per-Instance Cost Analysis

_Last updated: 2026-07-19_

This document defines how to track EC2 cost using AWS Cost Explorer and CloudWatch.

---

## 1. Per-Resource Cost Query

### By Instance Type

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"INSTANCE_TYPE"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Metrics.BlendedCost.Amount`

### By Tag (Environment/Application)

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}' \
  --group-by '[{"Type":"TAG","Key":"Environment"},{"Type":"TAG","Key":"Application"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Keys[]` (tag combinations)

---

## 2. Idle Resource Detection

### Running but CPU < 5% for 7 Consecutive Days

**Criteria**: `InstanceState = running` AND `CPUUtilization < 5%` for 7 days

```bash
# Step 1: List all running instances
aws ec2 describe-instances \
  --output json \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,Tags[?Key==`Name`].Value|[0]]'

# Step 2: Get CPU utilization for each instance over 7 days
aws cloudwatch get-metric-data \
  --output json \
  --metric-data-queries '[
    {
      "Id": "cpu_{{instance_id}}",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/EC2",
          "MetricName": "CPUUtilization",
          "Dimensions": [{"Name": "InstanceId", "Value": "{{instance_id}}"}]
        },
        "Period": 86400,
        "Stat": "Average"
      }
    }
  ]' \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z
```

**JSON path**: `MetricDataResults[].Values[]` (average CPU per day)

### Idle Instance Detection Output

```json
{
  "instance_id": "i-0abc123def456",
  "instance_type": "t3.medium",
  "idle_days": 7,
  "avg_cpu_utilization": 2.1,
  "estimated_monthly_cost": 30.00,
  "recommendation": "Stop or Terminate"
}
```

---

## 3. Savings Recommendations

### RI Coverage Report

```bash
aws ce get-savings-plans-coverage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}'
```

**JSON path**: `SavingsPlansCoverages[].Coverage[].CoveragePercentage`

### Savings Plans Utilization

```bash
aws ce get-savings-plans-coverage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon EC2"]}}'
```

---

## 4. Anomaly Detection

### Detect Sudden Spike in Instance Hours (> 50% Increase)

```bash
# Get daily instance-hours baseline
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/EC2 \
  --metric-name InstanceCount \
  --dimensions Name=InstanceState,Values=running \
  --start-time 2026-06-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Average
```

**JSON path**: `Datapoints[].Average`

### Anomaly Alert Output

```json
{
  "alert_type": "instance_hours_spike",
  "threshold_percent": 50,
  "baseline_avg": 45,
  "current_value": 78,
  "increase_percent": 73.3,
  "status": "ALERT"
}
```
