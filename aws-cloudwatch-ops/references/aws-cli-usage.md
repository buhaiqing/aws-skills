# AWS CLI Usage — CloudWatch

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Put alarm | `aws cloudwatch put-metric-alarm` | Empty (success) |
| Describe alarms | `aws cloudwatch describe-alarms` | `.MetricAlarms[]` |
| Delete alarms | `aws cloudwatch delete-alarms` | Empty (success) |
| List metrics | `aws cloudwatch list-metrics` | `.Metrics[]` |
| Get metric data | `aws cloudwatch get-metric-data` | `.MetricDataResults[]` |
| Put metric data | `aws cloudwatch put-metric-data` | Empty (success) |
| Put dashboard | `aws cloudwatch put-dashboard` | Empty (success) |
| List dashboards | `aws cloudwatch list-dashboards` | `.DashboardEntries[]` |
| Delete dashboard | `aws cloudwatch delete-dashboards` | Empty (success) |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Time Format
Use ISO 8601: `YYYY-MM-DDTHH:MM:SSZ`

### Period Units
- Seconds: 1, 5, 10, 30, 60
- Minutes: 60, 300, 900
- Hours: 3600
- Day: 86400

## Common Patterns

### Create Metric Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name HighCPU \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 60 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:my-topic \
  --region us-east-1 \
  --output json
```

### Create Alarm with Dimensions
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name InstanceHighCPU \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region us-east-1 \
  --output json
```

### Describe Alarms
```bash
# All alarms
aws cloudwatch describe-alarms --region us-east-1 --output json

# Specific alarm
aws cloudwatch describe-alarms --alarm-names HighCPU --region us-east-1 --output json

# By state
aws cloudwatch describe-alarms --state-value ALARM --region us-east-1 --output json
```

### Delete Alarm
```bash
aws cloudwatch delete-alarms --alarm-names HighCPU --region us-east-1 --output json
```

### List Available Metrics
```bash
# All metrics
aws cloudwatch list-metrics --region us-east-1 --output json

# By namespace
aws cloudwatch list-metrics --namespace AWS/EC2 --region us-east-1 --output json

# By metric name
aws cloudwatch list-metrics --namespace AWS/EC2 --metric-name CPUUtilization --region us-east-1 --output json
```

### Get Metric Statistics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistics Average \
  --period 300 \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-10T12:00:00Z \
  --region us-east-1 \
  --output json
```

### Put Custom Metric
```bash
aws cloudwatch put-metric-data \
  --namespace MyApplication \
  --metric-name RequestCount \
  --value 100 \
  --unit Count \
  --region us-east-1 \
  --output json

# With dimensions
aws cloudwatch put-metric-data \
  --namespace MyApplication \
  --metric-name RequestCount \
  --dimensions Name=Service,Value=API Name=Method,Value=GET \
  --value 50 \
  --region us-east-1 \
  --output json
```

### Get Metric Data (Multiple Queries)
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"cpu","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"Stat":"Average","Period":300}},
    {"Id":"mem","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"MemoryUtilization"},"Stat":"Average","Period":300}}
  ]' \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-10T12:00:00Z \
  --region us-east-1 \
  --output json
```

## Comparison Operators

| Operator | Description |
|----------|-------------|
| GreaterThanThreshold | Value > threshold |
| GreaterThanOrEqualToThreshold | Value >= threshold |
| LessThanThreshold | Value < threshold |
| LessThanOrEqualToThreshold | Value <= threshold |

## Statistics

| Statistic | Description |
|-----------|-------------|
| Average | Mean value |
| Sum | Total value |
| Minimum | Lowest value |
| Maximum | Highest value |
| SampleCount | Number of data points |
| pNN.NN | Percentile (e.g., p90, p95, p99) |

## CLI vs API Coverage Gap

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| PutMetricAlarm | ✅ | `put-metric-alarm` |
| DescribeAlarms | ✅ | `describe-alarms` |
| DeleteAlarms | ✅ | `delete-alarms` |
| ListMetrics | ✅ | `list-metrics` |
| GetMetricStatistics | ✅ | `get-metric-statistics` |
| GetMetricData | ✅ | `get-metric-data` |
| PutMetricData | ✅ | `put-metric-data` |
| PutDashboard | ✅ | `put-dashboard` |
| ListDashboards | ✅ | `list-dashboards` |
| DeleteDashboards | ✅ | `delete-dashboards` |
| PutCompositeAlarm | ✅ | `put-composite-alarm` |
| SetAlarmState | ✅ | `set-alarm-state` (testing only) |