---
name: aws-cloudwatch-ops
description: >-
  Use when managing CloudWatch alarms, metrics, dashboards, log groups, anomaly detection,
  logs insights, metric math, cost analysis, and observability. Invoke when user mentions
  "CloudWatch", "CW", "monitoring", "alarms", "logs", "insights", "anomaly", "metric math",
  "forecast", "dashboard", or needs AWS resource observability and alerting.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to CloudWatch endpoints.
metadata:
  author: aws
  version: "2.2.0"
  last_updated: "2026-05-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-elb-ops             # ELB metrics, alarm templates
    - aws-ec2-ops              # EC2 metric correlation
    - aws-vpc-ops              # VPC Flow Logs integration
    - aws-route53-ops          # DNS health check monitoring
    - aws-acm-ops              # Certificate expiry monitoring
    - aws-cloudtrail-ops       # API event correlation
---

# AWS CloudWatch Operations Skill

## Overview

Operational runbook for CloudWatch metrics, alarms, logs, dashboards, anomaly detection, and cost analysis.

## Trigger & Scope

### SHOULD Use When
- User mentions "CloudWatch", "CW", "metrics", "alarms", "monitoring"
- Task involves **metrics, alarms, dashboards, log groups, logs insights, anomaly detection, metric math, forecast, cost analysis**
- Keywords: alarm, metric, dashboard, threshold, namespace, dimension, anomaly, forecast, logs, insight, contributor, synthetics, cost
- **(AIOps)** ELB latency/error anomaly diagnosis via metrics and logs
- **(AIOps)** Certificate expiry monitoring via custom metrics
- **(AIOps)** Cross-module RCA: correlate ELB/EC2/VPC metrics
- **(AIOps)** Capacity planning via FORECAST for service modules
- Keywords: elb-monitoring, elb-anomaly, elb-capacity, elb-rca, cert-expiry, cross-module-rca

### SHOULD NOT Use When
- EC2 instance ops → `aws-ec2-ops`
- S3 bucket ops → `aws-s3-ops`
- RDS database ops → `aws-rds-ops`
- Lambda function code/version → `aws-lambda-ops`
- SSM runbook/command → `aws-ssm-ops`
- SNS topic/subscription → `aws-sns-ops`
- Auto Scaling group → `aws-ec2-ops`

## Placeholder Convention

| Token | Source | Notes |
|-------|--------|-------|
| `{{r.region}}` | User input or `{{env.AWS_DEFAULT_REGION}}` | Default `us-east-1` |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Fallback for `{{r.region}}` |
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Skip if using AWS_PROFILE/IAM |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Skip if using AWS_PROFILE/IAM |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temp creds only |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{env.AWS_ACCOUNT_ID}}` | Runtime env | Required for ARN construction |
| `{{u.*}}` | User input | Ask once; reuse |
| `{{o.*}}` | Last API response | Parse from JSON output |

## Config File Injection

`assets/example-config.yaml` contains `{{env.*}}` / `{{u.*}}` placeholders. Load `.env`, substitute, then use rendered config for CLI/SDK.

## FinOps Cost Awareness

- **Alarms**: $0.10/alarm/mo → use composite alarms
- **Dashboards**: $3/dashboard/mo (first 50 metrics free)
- **Custom Metrics**: $0.30/custom metric/mo → prefer built-in
- **Logs Ingestion**: $0.50/GB → set retention
- **Logs Insights**: $0.005/GB scanned → filter aggressively
- **Free Tier**: 10 custom metrics, 10 alarms, 3 dashboards, 5 GB log ingestion

### Cost Pre-flight (on explicit cost request)

```bash
aws cloudwatch describe-alarms --region {{r.region}} --output json | jq '.MetricAlarms | length'
aws cloudwatch list-dashboards --region {{r.region}} --output json | jq '.DashboardEntries | length'
```
```
Alarms(N): N≤10=$0/mo else $(N-10)×$0.10
Dashboards(M): M≤3=$0/mo else $(M-3)×$3.00
Tip: composite alarms / remove unused dashboards to reduce cost
```

## Shared Patterns

**Pre-flight**: All operations start with `aws --version` + `aws sts get-caller-identity`.

**Output**: All commands use `--region {{r.region}} --output json` (omitted in some snippets).

**Validate**: For create/update ops, use `describe-alarms` or equivalent read command to confirm.

**Common Recovery** (reused unless overridden):
| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix params; retry once |
| ResourceNotFound (404) | Verify resource exists |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

**boto3 fallback**: See [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md) → matching section.

## Operations

### OP: Create Alarm
`put-metric-alarm` — standard threshold-based alarm.
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{u.alarm}}" --metric-name "{{u.metric}}" --namespace "{{u.ns}}" \
  --statistic "{{u.stat}}" --period {{u.period}} --threshold {{u.th}} \
  --comparison-operator "{{u.op}}" --evaluation-periods {{u.eval}} \
  --alarm-actions "{{u.actions}}"
```
Pre-flight: Verify metric via `list-metrics`. **WARN** if `actions` empty (silent alarm).
ID update: re-run same `--alarm-name` with new params to modify.

### OP: Composite Alarm (FinOps)
`put-composite-alarm` — merges multiple conditions into one alarm (saves $0.10/mo each).
Alarm Rule syntax: `(ALARM("a") OR ALARM("b"))` — supports `AND`, `OR`, `NOT`, nesting.
```bash
# Pre-flight: verify referenced alarms exist
aws cloudwatch describe-alarms --alarm-names "{{u.ref1}}" "{{u.ref2}}"
```
```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "{{u.alarm}}-Composite" \
  --alarm-rule '(ALARM("{{u.ref1}}") OR ALARM("{{u.ref2}}"))' \
  --alarm-actions "{{u.actions}}"
```
| Recover Override | Action |
|-----------------|--------|
| LimitExceeded | HALT; delete unused alarms |

### OP: Anomaly Detection Alarm (AIOps)
`put-metric-alarm` with `ANOMALY_DETECTION_BAND` — ML learns seasonal patterns, dynamic threshold.
```bash
# Pre-flight: verify ≥ 2 weeks data
aws cloudwatch get-metric-statistics --namespace "{{u.ns}}" --metric-name "{{u.metric}}" \
  --statistics Average --period 3600 \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  | jq '.Datapoints | length'
```
```
Datapoints ≥ 336 (14d×24h) required. If insufficient, suggest static threshold.
```
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{u.alarm}}-Anomaly" --metric-name "{{u.metric}}" --namespace "{{u.ns}}" \
  --statistic "{{u.stat}}" --period {{u.period}} \
  --threshold-metric-id "ad" \
  --comparison-operator "LessThanLowerOrGreaterThanUpperThreshold" \
  --evaluation-periods {{u.eval}} \
  --metrics '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{u.ns}}","MetricName":"{{u.metric}}"},"Period":{{u.period}},"Stat":"{{u.stat}}"}},{"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1, {{u.deviation}})"}]'
```
| Parameter | Notes |
|-----------|-------|
| `deviation` | Default 2; range 1-6; higher = less sensitive |

| Recover Override | Action |
|-----------------|--------|
| InvalidParameterValue | Ensure `threshold-metric-id` matches `"ad"` |

### OP: Delete Alarm (Destructive)
**Safety Gate**: Explicit confirmation required.
```
Delete alarm {{u.alarm}}? IRREVERSIBLE.
```
```bash
aws cloudwatch delete-alarms --alarm-names "{{u.alarm}}"
```
Validate: `describe-alarms` → `.MetricAlarms` empty.
| Recover Override | Action |
|-----------------|--------|
| ResourceNotFound | Already deleted — treat as success |

### OP: Delete Insight Rules (Destructive)
**Safety Gate**: Explicit confirmation required.
```
Delete insight rule {{u.rule}}? Removes collected contributor data permanently.
```
```bash
aws cloudwatch delete-insight-rules --rule-names "{{u.rule}}"
```
Validate: `list-insight-rules` → rule absent.
| Recover Override | Action |
|-----------------|--------|
| ResourceNotFound | Already deleted — treat as success |

### OP: List Metrics & Alarms
List available metrics or alarm states (read-only, no pre-flight).
```bash
# Metrics by namespace
aws cloudwatch list-metrics --namespace "{{u.ns}}"
# All alarms
aws cloudwatch describe-alarms
# By alarm name
aws cloudwatch describe-alarms --alarm-names "{{u.alarm}}"
# By state
aws cloudwatch describe-alarms --state-value ALARM
```

### OP: Get Metric Data
`get-metric-data` — fetch time-series data for a metric.
```bash
# Pre-flight: verify metric exists
aws cloudwatch list-metrics --namespace "{{u.ns}}" --metric-name "{{u.metric}}"
```
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{u.ns}}","MetricName":"{{u.metric}}"},"Stat":"{{u.stat}}","Period":{{u.period}}}}]' \
  --start-time "{{u.start}}" --end-time "{{u.end}}" \
  | jq '.MetricDataResults[].Values | length'
```
```
Retrieved N datapoints. WARN if empty — expand time range.
```

### OP: Logs Insights (AIOps)
`logs start-query` + `logs get-query-results` — SQL-style log analysis.
```bash
# Pre-flight: verify log group
aws logs describe-log-groups --log-group-name-prefix "{{u.log}}"
```
```bash
# Start query
aws logs start-query --log-group-names "{{u.log}}" \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /(?i)(error|exception|fail)/ | stats count() by @logStream | sort count desc | limit 20'
```
Save `{{o.qid}}` from response. Poll with `get-query-results --query-id "{{o.qid}}"` until `status=Complete`.

| Query Pattern | String |
|---------------|--------|
| Error count/5m | `filter @message like /ERROR/ \| stats count() by bin(5m)` |
| Slow requests | `filter @duration > 3000 \| stats avg(@duration), max(@duration), count()` |
| Status breakdown | `parse @message /(?<status>\d{3})/ \| stats count() by status` |
| Top error streams | `filter @message like /(?i)error/ \| stats count() by @logStream \| sort count desc \| limit 10` |

| Recover Override | Action |
|-----------------|--------|
| MalformedQueryException | Fix syntax; retry |
| LimitExceededException | Max 5 concurrent queries per account |
| Timeout (>10min) | Narrow time range |

### OP: Forecast (AIOps+FinOps)
`get-metric-data` with `FORECAST` — predict trends for capacity/cost planning.
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{u.ns}}","MetricName":"{{u.metric}}"},"Stat":"{{u.stat}}","Period":3600}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}]' \
  --start-time "{{u.start}}" --end-time "{{u.end}}" \
  | jq '.MetricDataResults[] | select(.Id=="fc") | .Values'
```
Supports `linear` / `diff` / `mahalanobis` models. Forecast overload → scale-up, under-utilization → downsize.
Forecast data empty → insufficient history.

### OP: Create Dashboard
`put-dashboard` — monitoring panel for metrics.
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "{{u.dash}}" \
  --dashboard-body '{"widgets":[{"type":"metric","properties":{"metrics":[["{{u.ns}}","{{u.metric}}"]],"period":300,"stat":"Average"}}]}'
```
| Recover Override | Action |
|-----------------|--------|
| ConcurrentModification | Re-read and retry |

### OP: Set Log Retention (FinOps)
**Safety Gate**: Confirm with user (data loss).
```
Set retention to {{u.retention}}d? Logs older will be permanently deleted.
```
```bash
aws logs put-retention-policy --log-group-name "{{u.log}}" --retention-in-days {{u.retention}}
```
Validate: `describe-log-groups` → `.retentionInDays`.
| Recover Override | Action |
|-----------------|--------|
| InvalidParameterException | Valid values: 1,3,5,7,14,30,60,90,120,150,180,365,400,545,731,1827,3653 |

### OP: Diagnose Alarm
When user reports "alarm not triggering":
```bash
# 1. Check state
aws cloudwatch describe-alarms --alarm-names "{{u.alarm}}"
# 2. Check metric data (last 1h)
aws cloudwatch get-metric-statistics --namespace "{{u.ns}}" --metric-name "{{u.metric}}" \
  --statistics Average --period {{u.period}} \
  --dimensions Name="{{u.dim}}",Value="{{u.dim_val}}" \
  --start-time $(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  | jq '.Datapoints | length'
# 3. Check alarm history
aws cloudwatch describe-alarm-history --alarm-name "{{u.alarm}}"
```
| State Observation | Cause | Fix |
|---|---|---|
| OK, data exists | Threshold too high | Lower threshold |
| INSUFFICIENT_DATA | Wrong namespace/metric/dimensions | Verify metric path |
| ALARM, no notification | Missing alarm-actions | Add SNS ARN |
| No history | Newly created | Wait for next evaluation |
| No datapoints | Time range or metric wrong | Adjust range or verify metric |

## Cross-Cutting Scenarios

### Cost Anomaly RCA
```bash
aws cloudwatch get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges \
  --statistics Maximum --period 86400 \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z) --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region us-east-1 --output json
```
Cross-reference spikes with resource metrics (EC2 CPU, Lambda Invocations, DynamoDB Capacity). Recommend downsize/cleanup/right-size.

### Predictive Maintenance
Query FORECAST → if projected to exceed safe threshold within 7 days → alert → recommend scale-up.

### Cross-Skill: Three-Layer Inspection
CloudWatch as observability hub. Bottom-up chain:
```
Network Layer    ← aws-elb-ops + aws-vpc-ops
Resource Layer   ← aws-ec2-ops + aws-rds-ops + aws-elasticache-ops + aws-dynamodb-ops
Application Layer← aws-eks-ops
```
Trigger phrases:
> "帮我做一次全面运维巡检，包含根因分析和自治愈建议"
> "Run a full-stack inspection with root cause analysis and auto-healing recommendations"

See [references/layered-inspection-template.md](references/layered-inspection-template.md) for output format.

## Common Namespace-Metric Patterns

| Service | Namespace | Key Metrics |
|---------|-----------|-------------|
| EC2 | AWS/EC2 | CPUUtilization, NetworkIn/Out |
| S3 | AWS/S3 | BucketSizeBytes, NumberOfObjects |
| RDS | AWS/RDS | CPUUtilization, FreeStorageSpace |
| Lambda | AWS/Lambda | Invocations, Errors, Duration |
| ALB | AWS/ApplicationELB | TargetResponseTime, HTTPCode_Target_5XX, HealthyHostCount, UnHealthyHostCount, RequestCount, ActiveConnectionCount, ConsumedLCUs |
| NLB | AWS/NetworkELB | ActiveFlowCount, NewFlowCount, ProcessedBytes, HealthyHostCount |
| EKS (Container Insights) | AWS/ContainerInsights | pod_cpu_utilization, pod_memory_utilization, node_cpu_utilization, node_memory_utilization |

## ELB-Specific Monitoring Templates

### Anomaly Detection Alarm for ALB Request Count
```bash
# Pre-flight: verify ≥ 2 weeks metric data
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCount \
  --statistics Sum --period 3600 \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  | jq '.Datapoints | length'
```

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-RequestCount-Anomaly" \
  --alarm-description "AIOps: Seasonal anomaly detection for ALB request count" \
  --metrics '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":300,"Stat":"Sum"}},{"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1,2)"}]' \
  --threshold-metric-id "ad" \
  --comparison-operator "LessThanLowerOrGreaterThanUpperThreshold" \
  --evaluation-periods 2 \
  --alarm-actions "{{sns_arn}}"
```

### Latency Monitoring Alarm (p99)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-p99-Latency-High" \
  --alarm-description "AIOps: p99 latency exceeds 1000ms for 3 consecutive periods" \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistic p99 --period 60 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions "{{sns_arn}}"
```

### Health Composite Alarm (ELB + EC2)
```bash
# Create individual alarms first
aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-HealthyHosts-Low" \
  --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value={{tg_arn}} \
  --statistic Minimum --period 60 \
  --threshold {{min_healthy}} \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2

aws cloudwatch put-metric-alarm \
  --alarm-name "{{lb_name}}-5XX-Errors" \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistic Sum --period 60 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Composite: alert if BOTH health AND errors indicate backend issue
aws cloudwatch put-composite-alarm \
  --alarm-name "{{lb_name}}-Backend-Health-Composite" \
  --alarm-rule '(ALARM("{{lb_name}}-HealthyHosts-Low") OR ALARM("{{lb_name}}-5XX-Errors"))' \
  --alarm-actions "{{sns_arn}}"
  # Saves: $0.10/alarm/mo compared to 2 separate alarms
```

### ELB Health Dashboard Widget
```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "{{lb_arn}}", {"stat": "p99"}],
      ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", "{{tg_arn}}", {"stat": "Minimum"}],
      ["AWS/ApplicationELB", "HTTPCode_Target_5XX", "LoadBalancer", "{{lb_arn}}", {"stat": "Sum"}],
      [".", "RequestCount", ".", ".", {"stat": "Sum"}],
      ["AWS/ApplicationELB", "ActiveConnectionCount", "LoadBalancer", "{{lb_arn}}", {"stat": "Average"}]
    ],
    "period": 300,
    "stat": "Average",
    "region": "{{r.region}}",
    "title": "{{lb_name}} — Real-Time Health"
  }
}
```

### FORECAST: ELB Capacity Planning
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"ActiveConnectionCount","Dimensions":[{"Name":"LoadBalancer","Value":"{{lb_arn}}"}]},"Period":3600,"Stat":"Maximum"},"Label":"ActiveConnections"},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
  ]' \
  --start-time "$(date -d '-14 days' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Certificate Expiry Alarm (via custom metric)
```bash
# Publish certificate expiry as custom metric
aws cloudwatch put-metric-data \
  --namespace AWS/AIOps \
  --metric-data '[{"MetricName":"CertDaysToExpiry","Dimensions":[{"Name":"Domain","Value":"{{domain}}"}],"Value":{{days}}, "Unit":"Count"}]'

# Alarm when < 30 days
aws cloudwatch put-metric-alarm \
  --alarm-name "{{domain}}-Cert-Expiry" \
  --namespace AWS/AIOps \
  --metric-name CertDaysToExpiry \
  --dimensions Name=Domain,Value={{domain}} \
  --statistic Minimum --period 86400 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1
```

### Cross-Module: ELB → EC2 Latency Correlation Dashboard
```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "{{lb_arn}}", {"stat": "p99", "label": "ALB Latency"}],
      ["AWS/EC2", "CPUUtilization", "InstanceId", "{{instance_id}}", {"stat": "Average", "label": "EC2 CPU", "yAxis": "right"}],
      ["AWS/EC2", "NetworkIn", "InstanceId", "{{instance_id}}", {"stat": "Average", "yAxis": "right"}]
    ],
    "period": 300,
    "title": "Latency Correlation: ELB → Backend EC2"
  }
}
```

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, recommended). Every execution of
> `aws-cloudwatch-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `recommended` |
| `max_iterations` | `3` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-alarms` — IRREVERSIBLE; silent-failure guard (warn if alarm has no actions); confirm `DELETE_ALARMS <names>`
- `delete-insight-rules` — removes collected contributor data permanently
- `put-retention-policy` — logs older than retention period permanently deleted; confirm with user

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (alarm/metric name echoed from `describe-alarms` / `list-metrics`), A9 (metric data / log content secrets masked), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [Prompt Examples](references/prompt-examples.md) — 11 concrete user prompts
- [Layered Inspection Template](references/layered-inspection-template.md) — Cross-skill deep inspection
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)