# AWS CLI Usage — CloudWatch

_Latest update: 2026-06-13_

## Command Map

| Goal | CLI Command | JSON Output Path |
|------|-------------|------------------|
| Put alarm | `aws cloudwatch put-metric-alarm` | Empty (success) |
| Describe alarms | `aws cloudwatch describe-alarms` | `.MetricAlarms[]` |
| Delete alarms | `aws cloudwatch delete-alarms` | Empty (success) |
| List metrics | `aws cloudwatch list-metrics` | `.Metrics[]` |
| Get metric statistics | `aws cloudwatch get-metric-statistics` | `.Datapoints[]` |
| Get metric data | `aws cloudwatch get-metric-data` | `.MetricDataResults[]` |
| Put metric data | `aws cloudwatch put-metric-data` | Empty (success) |
| Put composite alarm | `aws cloudwatch put-composite-alarm` | Empty (success) |
| Put dashboard | `aws cloudwatch put-dashboard` | Empty (success) |
| List dashboards | `aws cloudwatch list-dashboards` | `.DashboardEntries[]` |
| Delete dashboard | `aws cloudwatch delete-dashboards` | Empty (success) |
| Start logs query | `aws logs start-query` | `.queryId` |
| Get query results | `aws logs get-query-results` | `.results`, `.status` |
| Put insight rule | `aws cloudwatch put-insight-rule` | Empty (success) |
| List insight rules | `aws cloudwatch list-insight-rules` | `.InsightRules[]` |

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

### Batch Metric Collection (for Capacity Forecast)
Collect 14-day hourly history for trend prediction. Pipe to Python for forecasting:
```bash
# 14-day hourly CPU history for EC2 instance
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value={{instance_id}} \
  --statistics Average \
  --period 3600 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region us-east-1 \
  --output json | jq '.Datapoints'
```

**Note**: AWS has no native `forecast` CLI. Use `get_metric_statistics` to collect history, then `scripts/capacity_forecast.py` (`predict_capacity()`) to compute trends.

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

### Get Metric Data with Metric Math (AIOps: Error Rate %)
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"errors","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Errors"},"Stat":"Sum","Period":300}},
    {"Id":"invocations","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Invocations"},"Stat":"Sum","Period":300}},
    {"Id":"error_rate","Expression":"(errors/invocations)*100","Label":"Error Rate %"}
  ]' \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-10T12:00:00Z \
  --region us-east-1 \
  --output json
```

### Forecast Metrics (AIOps+FinOps: 预测未来趋势)
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"Stat":"Average","Period":3600}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)", "Label":"7-Day Forecast"}
  ]' \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-28T00:00:00Z \
  --region us-east-1 \
  --output json
```

### Create Anomaly Detection Alarm (AIOps: ML 动态阈值)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name HighCPU-Anomaly \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold-metric-id "ad" \
  --comparison-operator "LessThanLowerOrGreaterThanUpperThreshold" \
  --evaluation-periods 2 \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"Period":300,"Stat":"Average"}},
    {"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1, 2)"}
  ]' \
  --region us-east-1 \
  --output json
```

### Create Composite Alarm (FinOps: 合并告警省钱)
```bash
aws cloudwatch put-composite-alarm \
  --alarm-name Production-Health-Composite \
  --alarm-rule '(ALARM("HighCPU") OR ALARM("HighMemory"))' \
  --alarm-actions arn:aws:sns:us-east-1:123456789:ops-topic \
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
| LessThanLowerOrGreaterThanUpperThreshold | Outside anomaly detection band |
| LessThanLowerThreshold | Below anomaly band lower bound |
| GreaterThanUpperThreshold | Above anomaly band upper bound |

## Statistics

| Statistic | Description |
|-----------|-------------|
| Average | Mean value |
| Sum | Total value |
| Minimum | Lowest value |
| Maximum | Highest value |
| SampleCount | Number of data points |
| pNN.NN | Percentile (e.g., p90, p95, p99) |

## Logs Insights (AIOps)

### Start Log Query
```bash
aws logs start-query \
  --log-group-names /aws/lambda/my-function \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /(?i)(error|exception|fail)/
    | stats count() by @logStream
    | sort count desc
    | limit 20' \
  --region us-east-1 \
  --output json
```

### Get Query Results
```bash
aws logs get-query-results --query-id "q-abc12345" --region us-east-1 --output json
```

### Logs Insights Query Patterns

| Scenario | Query String |
|----------|-------------|
| Error count per 5min | `fields @timestamp \| filter @message like /ERROR/ \| stats count() by bin(5m)` |
| Top error messages | `fields @message \| filter @message like /(?i)error/ \| stats count() by @message \| sort count desc \| limit 10` |
| Slow requests (>3s) | `fields @timestamp, @duration \| filter @duration > 3000 \| sort @duration desc` |
| Status code breakdown | `parse @message /(?<status>\d{3})/ \| stats count() by status` |
| P99 latency by hour | `stats pct(@duration, 99) by bin(1h)` |
| Lambda cold starts | `fields @timestamp \| filter @message like /INIT_START/ \| stats count() by bin(1h)` |

## Contributor Insights (AIOps)

Contributor Insights 自动识别日志中异常贡献者（如最多访问的 IP、最慢的 API）。

### Create Insight Rule
```bash
aws cloudwatch put-insight-rule \
  --rule-name TopErrorUsers \
  --rule-state ENABLED \
  --rule-definition '{
    "Schema": {"Name": "CloudWatchLogRule", "Version": 1},
    "AggregateOn": "Count",
    "Contribution": {
      "Keys": ["$.userIdentity.arn"],
      "Filters": [{"Match": "$.errorCode", "Comparison": "starts-with", "Value": "Access"}]
    },
    "LogGroupNames": ["/aws/cloudtrail/logs"]
  }' \
  --region us-east-1 \
  --output json
```

### List Insight Rules
```bash
aws cloudwatch list-insight-rules --region us-east-1 --output json
```

### Delete Insight Rules
```bash
aws cloudwatch delete-insight-rules --rule-names TopErrorUsers --region us-east-1 --output json
```

## Delete Dashboard (Destructive)

**Safety Gate**: confirm `DELETE_DASHBOARD <name>` before execution.

```bash
# Pre-flight: verify dashboard exists
aws cloudwatch get-dashboard --dashboard-name "{{user.dash}}" --region {{user.region}} --output json

aws cloudwatch delete-dashboards --dashboard-names "{{user.dash}}" --region {{user.region}} --output json
```

Validate: `list-dashboards` → dashboard absent.

## Metric Math Alarm (AIOps: Error Rate %)

```bash
# Pre-flight: verify Lambda metrics exist
aws cloudwatch list-metrics --namespace AWS/Lambda --metric-name Errors --region {{user.region}} --output json

aws cloudwatch put-metric-alarm \
  --alarm-name "{{user.alarm}}-ErrorRate" \
  --metrics '[
    {"Id":"errors","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Errors","Dimensions":[{"Name":"FunctionName","Value":"{{user.fn}}"}]},"Period":300,"Stat":"Sum"}},
    {"Id":"invocations","MetricStat":{"Metric":{"Namespace":"AWS/Lambda","MetricName":"Invocations","Dimensions":[{"Name":"FunctionName","Value":"{{user.fn}}"}]},"Period":300,"Stat":"Sum"}},
    {"Id":"error_rate","Expression":"(errors/invocations)*100","Label":"Error Rate %"}
  ]' \
  --threshold-metric-id "error_rate" \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions "{{user.actions}}" \
  --region {{user.region}} --output json
```

## CloudWatch Synthetics (Canary)

```bash
# Pre-flight: verify canary name not taken
aws synthetics describe-canaries --region {{user.region}} --output json \
  | jq '.Canaries[] | select(.Name=="{{user.canary}}")'

aws synthetics create-canary \
  --name "{{user.canary}}" \
  --artifact-s3-location "s3://{{user.bucket}}/canary-artifacts/" \
  --execution-role-arn "{{user.role_arn}}" \
  --schedule expression="rate(5 minutes)" \
  --runtime-version syn-nodejs-puppeteer-9.1 \
  --code '{"Handler":"canary.handler","Script":"const synthetics = require(\"Synthetics\"); exports.handler = async () => { await synthetics.executeStep(\"heartbeat\", async () => { await synthetics.getPage(); }); };"}' \
  --region {{user.region}} --output json
```

Validate: `describe-canaries` → `Status.State=RUNNING`. Delete: `delete-canary --name` (destructive, confirm required).

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
| StartQuery | ✅ | `logs start-query` |
| GetQueryResults | ✅ | `logs get-query-results` |
| PutInsightRule | ✅ | `cloudwatch put-insight-rule` |
| ListInsightRules | ✅ | `cloudwatch list-insight-rules` |
| DeleteInsightRules | ✅ | `cloudwatch delete-insight-rules` |
| CreateCanary | ✅ | `synthetics create-canary` |
| DescribeCanaries | ✅ | `synthetics describe-canaries` |
| DeleteCanary | ✅ | `synthetics delete-canary` |