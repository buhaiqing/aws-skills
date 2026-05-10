# Core Concepts — CloudWatch

## What is Amazon CloudWatch

- **Purpose**: Monitoring and observability for AWS resources
- **Category**: Management & Governance
- **Console**: https://console.aws.amazon.com/cloudwatch/
- **Docs**: https://docs.aws.amazon.com/cloudwatch/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Alarm | Threshold-based alert | /cloudwatch/home#alarms |
| Metric | Time-series data point | /cloudwatch/home#metrics |
| Dashboard | Visual monitoring panel | /cloudwatch/home#dashboards |
| Log Group | Log aggregation | /cloudwatch/home#logs |
| Log Stream | Log sequence within group | Log Group → Log streams |

## Metric Structure

```
Namespace/MetricName[Dimension:Value]
Example: AWS/EC2/CPUUtilization[InstanceId:i-12345]
```

| Component | Description | Example |
|-----------|-------------|---------|
| Namespace | Service container | AWS/EC2 |
| MetricName | Metric identifier | CPUUtilization |
| Dimension | Resource filter | InstanceId=i-12345 |

## Common Namespace-Metric Patterns

| Service | Namespace | Key Metrics |
|---------|-----------|-------------|
| EC2 | AWS/EC2 | CPUUtilization, NetworkIn/Out, StatusCheckFailed |
| S3 | AWS/S3 | BucketSizeBytes, NumberOfObjects |
| RDS | AWS/RDS | CPUUtilization, FreeStorageSpace, ReadIOPS |
| Lambda | AWS/Lambda | Invocations, Errors, Duration, Throttles |
| ELB | AWS/ELB | RequestCount, TargetResponseTime, HTTPCode_Target_5XX |
| DynamoDB | AWS/DynamoDB | ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits |

## Alarm States

| State | Description | Action |
|-------|-------------|--------|
| OK | Within threshold | None |
| ALARM | Breaches threshold | Execute actions (SNS, Auto Scaling) |
| INSUFFICIENT_DATA | No data available | Optional action |

## Alarm Evaluation

| Parameter | Description | Example |
|-----------|-------------|---------|
| Threshold | Trigger value | 80 (percent) |
| ComparisonOperator | Breach condition | GreaterThanThreshold |
| EvaluationPeriods | Number of periods to check | 3 |
| DatapointsToAlarm | Minimum breaches | 2 (of 3 periods) |
| Period | Time window | 60 seconds |

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Alarms per account | 500 | Yes (up to 10,000) |
| Metrics per dashboard | 100 | No |
| Dashboards per account | 500 | Yes |
| Metric data points per PutMetricData | 20 | No |
| Custom metrics per account | 10,000 | Yes |

## Period Constraints

| Resolution | Valid Periods |
|------------|---------------|
| Standard (60s) | 60, 300, 900, 3600, 86400 |
| High resolution (1s/5s) | 1, 5, 10, 30, 60 |

## Pricing Model

- **Metrics**: $0.30 per custom metric/month
- **Alarms**: $0.10 per alarm/month
- **Logs**: $0.50 per GB ingested, $0.03 per GB stored
- **Dashboards**: $3.00 per dashboard/month (up to 50 metrics free)
- **Free tier**: 10 custom metrics, 10 alarms, 3 dashboards

## Best Practices

### Monitoring
- Use consolidated dashboards
- Set meaningful thresholds (avoid noise)
- Use anomaly detection for dynamic thresholds
- Enable detailed monitoring for EC2 (1-minute vs 5-minute)

### Alerts
- Use SNS for notifications
- Set OK actions for recovery alerts
- Use composite alarms for complex logic
- Avoid overly sensitive thresholds

### Logs
- Use subscription filters for real-time processing
- Set retention policies (default infinite)
- Use metric filters to extract metrics from logs