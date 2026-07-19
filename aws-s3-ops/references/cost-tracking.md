# Cost Tracking — S3 per-Bucket Cost Analysis

_Last updated: 2026-07-19_

This document defines how to track S3 cost using AWS Cost Explorer and S3 Storage Lens.

---

## 1. Per-Resource Cost Query

### By Linked Account

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity DAILY \
  --metrics "BlendedCost" "UnblendedCost" "UsageQuantity" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Simple Storage Service"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Metrics.BlendedCost.Amount`

### By Storage Type

```bash
aws ce get-cost-and-usage \
  --output json \
  --time-period Start=2026-07-01,End=2026-07-19 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Simple Storage Service"]}}' \
  --group-by '[{"Type":"DIMENSION","Key":"STORAGE_TYPE"}]'
```

**JSON path**: `ResultsByTime[].Groups[].Keys[]` (storage types)

---

## 2. Idle Resource Detection

### Objects Not Modified for > 1 Year + Not in IA/Glacier

**Criteria**: `LastModified > 365 days` AND NOT in `INTELLIGENT_TIERING` or `GLACIER` storage class

```bash
# Step 1: List all buckets
aws s3api list-buckets \
  --output json \
  --query 'Buckets[].[Name,CreationDate]'

# Step 2: Get bucket size and object count via Storage Lens
aws s3 get-storage-lens-configuration \
  --output json \
  --config-id default \
  --region {{env.AWS_DEFAULT_REGION}}
```

### List Objects Not Accessed in 1 Year

```bash
aws s3api list-objects-v2 \
  --output json \
  --bucket "{{user.bucket_name}}" \
  --query 'Contents[?LastModified<`2025-07-19`]|[?StorageClass==`STANDARD`]|[0:20]'
```

**JSON path**: `Contents[].Key` (object keys), `Contents[].Size` (bytes)

### Idle Bucket Detection Output

```json
{
  "bucket_name": "legacy-app-assets",
  "object_count": 12500,
  "total_size_gb": 45.3,
  "oldest_object_age_days": 420,
  "storage_class": "STANDARD",
  "estimated_monthly_cost": 10.30,
  "recommendation": "Migrate to Intelligent-Tiering or Glacier"
}
```

---

## 3. Savings Recommendations

### Intelligent-Tiering Migration Analysis

```bash
# Get current storage class distribution
aws s3api list-object-versions \
  --output json \
  --bucket "{{user.bucket_name}}" \
  --query 'Versions[].[Key,StorageClass,Size]'
```

### S3 Select Cost Comparison

```bash
# Get request rates for cost comparison
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/S3 \
  --metric-name SelectRequests \
  --dimensions Name=BucketName,Value={{user.bucket_name}} \
  --start-time 2026-07-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Sum
```

### Storage Tiering Savings Report

```json
{
  "bucket_name": "data-archive",
  "current_tier": "STANDARD",
  "recommended_tier": "INTELLIGENT_TIERING",
  "size_gb": 500,
  "estimated_monthly_savings": 11.50,
  "potential_annual_savings": 138.00
}
```

---

## 4. Anomaly Detection

### Storage Volume Spike Detection (> 50% Increase)

```bash
# Get bucket size metrics via Storage Lens
aws s3 get-storage-lens-configuration \
  --output json \
  --config-id default \
  --region {{env.AWS_DEFAULT_REGION}} \
  --query 'StorageLensConfiguration.S3BucketDestination.Encryption`
```

### Storage Size Trend Analysis

```bash
aws cloudwatch get-metric-statistics \
  --output json \
  --namespace AWS/S3 \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value={{user.bucket_name}} Name=StorageType,Value=StandardStorage \
  --start-time 2026-06-01T00:00:00Z \
  --end-time 2026-07-19T00:00:00Z \
  --period 86400 \
  --statistics Average
```

**JSON path**: `Datapoints[].Average` (bytes)

### Anomaly Alert Output

```json
{
  "alert_type": "storage_volume_spike",
  "bucket_name": "uploads-prod",
  "baseline_gb": 100,
  "current_gb": 165,
  "increase_percent": 65,
  "additional_monthly_cost_estimate": 14.30,
  "status": "ALERT"
}
```
