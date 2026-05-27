# Core Concepts — CloudWatch

_Latest update: 2026-05-28_

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
| Synthetics Canary | Programmatic browser/API monitoring | /cloudwatch/home#synthetics |
| Contributor Insights Rule | Top-N contributor analysis from logs | /cloudwatch/home#contributor-insights |

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
| EKS (Container Insights) | AWS/ContainerInsights | pod_cpu_utilization, pod_memory_utilization, node_cpu_utilization, node_memory_utilization, node_network_total_bytes |

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
- **Logs**: $0.50 per GB ingested, $0.03 per GB stored, **$0.005/GB scanned** (Logs Insights queries)
- **Dashboards**: $3.00 per dashboard/month (up to 50 metrics free)
- **Contributor Insights**: free (cost = underlying log scan pricing)
- **Amazon Managed Prometheus**: ~$0.03 per million samples ingested (alternative to custom CloudWatch metrics)
- **Amazon Managed Grafana**: $9/workspace/month + per-active-user pricing
- **Free tier**: 10 custom metrics, 10 alarms, 3 dashboards, 5 GB log ingestion

## AIOps: Anomaly Detection

CloudWatch Anomaly Detection uses an ML model to learn the baseline behavior patterns of a metric (daily/weekly seasonality), without manual static thresholds.

### How it works
- Model analyzes the last 2+ weeks of historical data
- Generates a dynamic upper/lower band (Anomaly Detection Band)
- Deviation factor: `1`=tight (sensitive), `6`=loose (insensitive), default `2`
- Comparison operator: `LessThanLowerOrGreaterThanUpperThreshold`
- **Model retrains hourly** with new incoming data

### Pre-flight accuracy note
The pre-flight check uses `--period 3600` to count datapoints over 30 days. For metrics with sparse reporting intervals (e.g., >6h), this may undercount. Use `--period <native_period>` for precision.

### When to use
| Scenario | Static Threshold | Anomaly Detection |
|----------|-----------------|-------------------|
| Stable metrics (e.g., disk usage) | Recommended | Over-engineered |
| Seasonal metrics (e.g., request count) | Frequent false alarms | Auto-adapts |
| New service, no history | Use static first | Needs 2 weeks of data |
| Traffic spikes on events | Cannot predict | Auto-identifies anomalies |

## AIOps: Logs Insights

CloudWatch Logs Insights provides a SQL-style log query engine for fast retrieval and aggregation across GB/TB-scale logs.

- **Query engine**: supports `fields`, `filter`, `stats`, `sort`, `limit`, `parse`, `bin` keywords
- **Data scope**: up to 10TB per query, up to 1 year lookback, up to 15 min runtime
- **Limits**: max 5 concurrent queries per account
- **Pricing**: $0.005/GB scanned

### Common Query Syntax
```
fields @timestamp, @message                     # 选择字段
filter @message like /(?i)error/                 # 过滤（大小写不敏感）
stats count() by bin(5m)                         # 聚合统计
parse @message /duration=(?<dur>\d+)/            # 正则提取
sort @timestamp desc                             # 排序
limit 20                                         # 限制结果
```

## AIOps: Contributor Insights

Contributor Insights automatically analyzes logs to identify "abnormal contributors" — e.g., most erroring users, slowest API routes, highest-frequency IPs.

- **Rule definition**: specify log group, matching JSON fields (Keys), filter conditions (Filters)
- **Aggregation**: Count / Sum / Average
- **Use cases**: access log analysis, API error attribution, security auditing

## AIOps: Metric Math

Metric Math allows mathematical computation across multiple metrics in `get-metric-data`:

| Function | Description | Use Case |
|----------|-------------|----------|
| `METRICS()` | Reference other Ids | Combine multiple metrics |
| `ANOMALY_DETECTION_BAND(m, N)` | ML anomaly detection band | Dynamic threshold alarms |
| `FORECAST(m, model, periods)` | Trend prediction | Capacity planning |
| `rate(m)` | Calculate rate of change | Burst detection |
| `diff(m)` | Calculate difference | Period-over-period analysis |
| `IF(m>t, m, 0)` | Conditional calculation | Filter outliers |

**Supported models**: `"linear"` (linear), `"diff"` (differential), `"mahalanobis"` (Mahalanobis distance)

**Model retraining**: Anomaly Detection model retrains hourly with new data.

## Additional Capabilities (Partial Coverage)

### CloudWatch Synthetics
- **Canaries**: Node.js/Puppeteer scripts that run on a schedule to monitor endpoints and APIs
- **Heartbeat monitoring**: Ping endpoints from AWS-managed locations
- **Visual monitoring**: Screenshot-based regression detection
- **Blueprint templates**: Heartbeat, API Canary, Broken Link Checker
- **Cost**: $0.0012 per canary run per location

### Metric Streams
- **Purpose**: Real-time streaming of CloudWatch metrics to AWS services (Firehose) or third-party destinations (Datadog, Splunk, New Relic, etc.)
- **Filtering**: Stream only selected namespaces/metrics via filter rules
- **Pricing**: $0.01 per 100,000 metric updates streamed
- **Use case**: Replace pull-based `get-metric-data` with push-based streaming for real-time dashboards

## FinOps: Cost Management

### Cost Control Strategies

| Strategy | Action | Expected Savings |
|----------|--------|-----------------|
| Set log retention | `aws logs put-retention-policy --log-group-name NAME --retention-in-days 90` | Linear with storage |
| Merge alarms to composite | `put-composite-alarm` | $0.10/alarm/month → halved |
| Reduce custom metrics | Reuse built-in AWS metrics, merge low-frequency | $0.30/custom metric/month |
| Optimize dashboards | Consolidate into fewer dashboards | $3/dashboard/month (beyond 3 free) |
| Logs to S3 cold storage | `put-subscription-filter` → S3 Glacier | ~1/3 of CloudWatch Logs cost |
| Use high-res cautiously | Standard 60s vs High-res 1s | High-res carries higher pricing |
| Migrate custom metrics to AMP | Amazon Managed Prometheus | ~$0.03/million samples vs $0.30/custom metric |

### Monthly Cost Calculator
| Resource | Unit Price | Free Tier | Calculation |
|----------|-----------|-----------|-------------|
| Alarm | $0.10/mo | 10 alarms | (N-10) × $0.10 |
| Custom Metric | $0.30/mo | 10 metrics | (M-10) × $0.30 |
| Dashboard | $3.00/mo | 3 dashboards | (D-3) × $3.00 |
| Log Ingested | $0.50/GB | 5 GB | (G-5) × $0.50 |
| Log Stored | $0.03/GB/mo | None | S × $0.03 |
| Logs Insights Scanned | $0.005/GB | None | Q × $0.005 |

## Alarm Actions (Beyond SNS)

CloudWatch alarms can trigger multiple action targets:

| Action Type | ARN Pattern | Use Case |
|-------------|-------------|----------|
| SNS Topic | `arn:aws:sns:region:account:topic-name` | Email, SMS, Lambda, SQS notification |
| Auto Scaling | `arn:aws:autoscaling:region:account:scalingPolicy:policy-id` | Auto scale EC2/ECS/EKS |
| EC2 Action | `arn:aws:automate:region:ec2:stop/terminate/reboot/recover` | Stop unhealthy instance |
| Systems Manager | `arn:aws:ssm:region:account:automation-definition/name:version` | Run SSM runbook on alarm |
| Lambda | `arn:aws:lambda:region:account:function:function-name` | Custom remediation logic |

**Cross-skill integration**:
- "Create alarm that reboots EC2 on high CPU" → use EC2 Action (not `aws-ec2-ops` directly)
- "Run SSM diagnostics on high memory alarm" → use SSM Automation Action
- "Notify on-call via PagerDuty" → configure SNS → PagerDuty webhook

## Best Practices

### Monitoring
- Use consolidated dashboards
- Set meaningful thresholds (avoid noise)
- Use anomaly detection for dynamic thresholds
- Enable detailed monitoring for EC2 (1-minute vs 5-minute)
- Leverage Container Insights for EKS workload monitoring
- Use Metric Math for derived metrics (error rate, utilization %)

### Alerts
- Use SNS for notifications
- Set OK actions for recovery alerts
- Use composite alarms for complex logic
- Avoid overly sensitive thresholds
- Prescribe both `--alarm-actions` (trigger) and `--ok-actions` (recovery)
- **AIOps**: Prefer anomaly detection for metrics with seasonal patterns
- **FinOps**: Use composite alarms to reduce alarm count and cost

### Logs
- Use subscription filters for real-time processing
- Set retention policies (default infinite, but costly)
- Use metric filters to extract metrics from logs
- Use Logs Insights for ad-hoc log analysis
- **FinOps**: Set retention to 90/30/7 days based on log criticality