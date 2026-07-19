# Cost Tracking — RDS per-Instance Cost Analysis

_Last updated: 2026-07-19_

This document defines how to track RDS cost using AWS Cost Explorer and CloudWatch.

---

## 1. Per-Resource Cost Query

### By Database Engine

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service (RDS)"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"DATABASE_ENGINE"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Metrics.BlendedCost.Amount`

### By Tag (Environment/Application)

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service (RDS)"]}}' \
  --group-by '[{"Type":"TAG","Key":"Environment"},{"Type":"TAG","Key":"Application"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Keys[]` (tag combinations)

---

## 2. Idle Resource Detection

### DatabaseConnections = 0 for 7 Consecutive Days

**Criteria**: `DatabaseConnections = 0` for 7 days

```bash
# Step 1: List all RDS instances
aws rds describe-db-instances \
  --output json \
  --query 'DBInstances[].[DBInstanceArn,DBInstanceIdentifier,Engine,DBInstanceClass]'

# Step 2: Check connection count for each instance over 7 days
aws cloudwatch get-metric-data \
  --output json \
  --metric-data-queries '[
    {
      "Id": "conn_{{db_instance_id}}",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/RDS",
          "MetricName": "DatabaseConnections",
          "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "{{db_instance_id}}"}]
        },
        "Period": 3600,
        "Stat": "Sum"
      }
    }
  ]' \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z
```

**JSON path**: `MetricDataResults[].Values[]` (sum of connections per hour)

### Idle RDS Detection Output

```json
{
  "db_instance_id": "rds-staging-db",
  "engine": "mysql",
  "db_instance_class": "db.t3.medium",
  "idle_days": 7,
  "total_connections": 0,
  "estimated_monthly_cost": 45.00,
  "recommendation": "Stop or Delete"
}
```

---

## 3. Savings Recommendations

### RI Coverage by Engine

```bash
aws ce get-reservation-coverage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service (RDS)"]}}'
```

**JSON path**: `CoveragesByTime[].Coverage[].CoveragePercentage`

### Multi-AZ vs Single-AZ Cost Delta

```bash
# Get instance pricing for comparison
aws rds describe-db-instance-attributes \
  --output json \
  --db-instance-identifier "{{db_instance_id}}"
```

### Idle RDS Savings Report

```json
{
  "total_idle_instances": 3,
  "estimated_monthly_savings": 135.00,
  "potential_annual_savings": 1620.00
}
```

---

## 4. Anomaly Detection

### Storage Burst Detection

```bash
# Get RDS storage metrics
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value={{db_instance_id}} \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Average
```

**JSON path**: `Datapoints[].Average` (bytes)

### I/O Cost Anomaly

```bash
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/RDS \
  --metric-name DiskQueueDepth \
  --dimensions Name=DBInstanceIdentifier,Value={{db_instance_id}} \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Anomaly Alert Output

```json
{
  "alert_type": "storage_burst",
  "db_instance_id": "rds-prod-db",
  "baseline_gb": 500,
  "current_gb": 750,
  "increase_percent": 50,
  "additional_monthly_cost": 25.00,
  "status": "ALERT"
}
```
