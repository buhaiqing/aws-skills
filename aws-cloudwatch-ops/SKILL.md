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
  version: "2.5.0"
  last_updated: "2026-06-26"
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
    - aws-elb-ops
    - aws-ec2-ops
    - aws-vpc-ops
    - aws-route53-ops
    - aws-acm-ops
    - aws-cloudtrail-ops
    - aws-aurora-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'capacity-forecast']
    produces_facts: ['metric', 'log']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS CloudWatch Operations Skill

## Common JSON Paths (Centralized)

```
# Alarms/Composite: .MetricAlarms[] / .CompositeAlarms[] → AlarmName, StateValue, MetricName, Namespace
# Metrics/Data:     .Metrics[] / .MetricDataResults[] / .Datapoints[]
# Dashboards:       .DashboardEntries[].DashboardName
# Logs:             .logGroups[]; start-query → .queryId; get-query-results → .status, .results
# Insights/Canary:  .InsightRules[] / .Canaries[].{Name,Status}
```

## Overview

AWS CloudWatch provides observability for AWS resources and applications. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "CloudWatch", "CW", metrics, alarms, monitoring, logs, dashboards
- Task: **alarms, metrics, dashboards, log groups, Logs Insights, anomaly detection, metric math, FORECAST, Contributor Insights, Synthetics**
- **(AIOps)** cross-module RCA, capacity FORECAST, cert-expiry metrics; keywords: elb-monitoring, elb-rca, cert-expiry

### SHOULD NOT Use When
- EC2 → `aws-ec2-ops` | S3 → `aws-s3-ops` | RDS → `aws-rds-ops` | Aurora → `aws-aurora-ops`
- Lambda code → `aws-lambda-ops` | SSM → `aws-ssm-ops` | SNS → `aws-sns-ops`
- ASG → `aws-autoscaling-ops` | ELB resource ops → `aws-elb-ops`

### Delegation
ELB ARNs/health → `aws-elb-ops` | Certs → `aws-acm-ops` | VPC Flow Logs → `aws-vpc-ops`
Patrol → `aws-aiops-cruise` | Orchestrator → `aws-aiops-orchestrator`
Layered inspection + AIOps scenarios → [references/layered-inspection-template.md](references/layered-inspection-template.md), [references/aiops-scenarios.md](references/aiops-scenarios.md)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temp creds only |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Fallback for `{{user.region}}` |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{user.region}}` | User input or env | Default `us-east-1` |
| `{{user.alarm}}` | User input | Alarm name |
| `{{user.ns}}` | User input | Namespace (e.g. `AWS/EC2`) |
| `{{user.metric}}` | User input | Metric name (e.g. `CPUUtilization`) |
| `{{user.log}}` | User input | Log group name |
| `{{user.dash}}` | User input | Dashboard name |
| `{{user.fn}}` | User input | Lambda function name |
| `{{user.actions}}` | User input | SNS ARN or alarm actions |
| `{{output.qid}}` | API response | `.queryId` from `start-query` |
| `{{output.*}}` | Last response | Parse per JSON paths above |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.alarm}}` | User input | Ask once; substitute |
| `{{user.ns}}` | User input | Ask once; substitute |

Before using `example-config.yaml`:
1. Load `.env` from project root (if present)
2. Substitute `{{env.*}}` placeholders with loaded values
3. Collect `{{user.*}}` values from user input
4. Use rendered config for CLI/SDK commands

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Common Pre-flight Steps (all ops)

#### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

#### Step 2: Load & Verify Credentials
```bash
aws sts get-caller-identity --output json
```
Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   AWS_ACCESS_KEY_ID=**** (masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```
On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws cloudwatch list-metrics --region {{user.region}}` | Suggest valid region |

### Operation: Create Metric Alarm

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{user.alarm}}" \
  --metric-name "{{user.metric}}" \
  --namespace "{{user.ns}}" \
  --statistic Average \
  --period 60 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions "{{user.actions}}" \
  --region "{{user.region}}" \
  --output json
```
Warn if `--alarm-actions` is empty — alarm will notify no one.

#### Execute — boto3 (Fallback)
```python
client.put_metric_alarm(
    AlarmName='{{user.alarm}}',
    MetricName='{{user.metric}}',
    Namespace='{{user.ns}}',
    Statistic='Average',
    Period=60,
    Threshold=80,
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=3,
    AlarmActions=['{{user.actions}}']
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}"` → confirm `StateValue` is not `INSUFFICIENT_DATA` and alarm exists.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix threshold/operator; retry once |
| LimitExceeded | HALT — delete unused alarms first |
| ThrottlingException | Backoff; retry 3x |
| InternalError | Retry 3x; HALT |

### Operation: Create Alarm with Dimensions

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{user.alarm}}-InstanceHighCPU" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_metric_alarm(
    AlarmName='{{user.alarm}}-InstanceHighCPU',
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
    Statistic='Average',
    Period=300,
    Threshold=90,
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}-InstanceHighCPU"` → confirm dimensions match.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix params; retry once |
| LimitExceeded | HALT — delete unused alarms |
| ThrottlingException | Backoff; retry 3x |
| InternalError | Retry 3x; HALT |

### Operation: Create Composite Alarm

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-composite-alarm \
  --alarm-name "{{user.alarm}}-Composite" \
  --alarm-rule '(ALARM("HighCPU") OR ALARM("HighMemory"))' \
  --alarm-actions "{{user.actions}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_composite_alarm(
    AlarmName='{{user.alarm}}-Composite',
    AlarmRule='(ALARM("HighCPU") OR ALARM("HighMemory"))',
    AlarmActions=['{{user.actions}}']
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}-Composite"` → confirm alarm exists and `Type` is `CompositeAlarm`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix alarm rule; retry once |
| LimitExceeded | HALT |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create Anomaly Detection Alarm

#### Pre-flight
Verify metric has at least 14 days of data for anomaly detection to work.

```bash
aws cloudwatch get-metric-statistics --namespace "{{user.ns}}" --metric-name "{{user.metric}}" \
  --statistics Average --period 3600 \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region "{{user.region}}" --output json | jq '.Datapoints | length'
```
Warn if `< 336` (14 days × 24 hours).

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{user.alarm}}-Anomaly" \
  --metric-name "{{user.metric}}" \
  --namespace "{{user.ns}}" \
  --statistic Average \
  --period 300 \
  --comparison-operator "LessThanLowerOrGreaterThanUpperThreshold" \
  --evaluation-periods 2 \
  --threshold-metric-id "ad" \
  --metrics '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{user.ns}}","MetricName":"{{user.metric}}"},"Period":300,"Stat":"Average"}},
    {"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1, 2)"}
  ]' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_metric_alarm(
    AlarmName='{{user.alarm}}-Anomaly',
    MetricName='{{user.metric}}',
    Namespace='{{user.ns}}',
    Statistic='Average',
    Period=300,
    ComparisonOperator='LessThanLowerOrGreaterThanUpperThreshold',
    EvaluationPeriods=2,
    ThresholdMetricId='ad',
    Metrics=[
        {'Id': 'm1', 'MetricStat': {'Metric': {'Namespace': '{{user.ns}}', 'MetricName': '{{user.metric}}'}, 'Period': 300, 'Stat': 'Average'}},
        {'Id': 'ad', 'Expression': 'ANOMALY_DETECTION_BAND(m1, 2)'}
    ]
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}-Anomaly"` → confirm `ThresholdMetricId` is `ad`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix metric/band; retry once |
| InsufficientData | HALT — need ≥14 days metric data |
| ThrottlingException | Backoff; retry 3x |

### Operation: Delete Alarm

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Pre-flight
Identify alarms to delete:
```bash
aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}" --region "{{user.region}}" --output json
```

#### Execute — CLI (Primary)
```bash
aws cloudwatch delete-alarms --alarm-names "{{user.alarm}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_alarms(AlarmNames=['{{user.alarm}}'])
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}"` → alarm not found (empty list).

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFound | HALT — alarm does not exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Describe / List Alarms

#### Execute — CLI (Primary)
```bash
# All alarms
aws cloudwatch describe-alarms --region "{{user.region}}" --output json

# Specific alarm
aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}" --region "{{user.region}}" --output json

# By state
aws cloudwatch describe-alarms --state-value ALARM --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.describe_alarms()
for alarm in response['MetricAlarms']:
    print(f"{alarm['AlarmName']} - {alarm['StateValue']}")
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Check response contains expected alarms.

#### Recover
| Error | Action |
|-------|--------|
| ThrottlingException | Backoff; retry 3x |
| InternalError | Retry 3x; HALT |

### Operation: List Metrics

#### Execute — CLI (Primary)
```bash
# All metrics
aws cloudwatch list-metrics --region "{{user.region}}" --output json

# By namespace
aws cloudwatch list-metrics --namespace "{{user.ns}}" --region "{{user.region}}" --output json

# By metric name
aws cloudwatch list-metrics --namespace "{{user.ns}}" --metric-name "{{user.metric}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
paginator = client.get_paginator('list_metrics')
for page in paginator.paginate(Namespace='{{user.ns}}'):
    for m in page['Metrics']:
        print(m['MetricName'])
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Check response contains metrics.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix namespace/metric; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: Get Metric Statistics

#### Execute — CLI (Primary)
```bash
aws cloudwatch get-metric-statistics \
  --namespace "{{user.ns}}" \
  --metric-name "{{user.metric}}" \
  --statistics Average \
  --period 300 \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-10T12:00:00Z \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
from datetime import datetime, timedelta
response = client.get_metric_statistics(
    Namespace='{{user.ns}}',
    MetricName='{{user.metric}}',
    Statistics=['Average'],
    Period=300,
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow()
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Check `.Datapoints` is not empty.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix time range/statistics; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: Get Metric Data (Multi-Query)

#### Execute — CLI (Primary)
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{user.ns}}","MetricName":"{{user.metric}}"},"Stat":"Average","Period":300}}
  ]' \
  --start-time 2026-05-10T00:00:00Z \
  --end-time 2026-05-10T12:00:00Z \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.get_metric_data(
    MetricDataQueries=[
        {'Id': 'm1', 'MetricStat': {'Metric': {'Namespace': '{{user.ns}}', 'MetricName': '{{user.metric}}'}, 'Stat': 'Average', 'Period': 300}}
    ],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow()
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Check `.MetricDataResults[]` contains results.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix query expression; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: Put Custom Metric

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-metric-data \
  --namespace "{{user.ns}}" \
  --metric-name "{{user.metric}}" \
  --value 100 \
  --unit Count \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_metric_data(
    Namespace='{{user.ns}}',
    MetricData=[{'MetricName': '{{user.metric}}', 'Value': 100, 'Unit': 'Count'}]
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
No direct validation. Verify with `aws cloudwatch list-metrics --namespace "{{user.ns}}" --metric-name "{{user.metric}}"`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix metric data; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: FORECAST Metric Trend

#### Pre-flight
Ensure sufficient historical data (≥14 days recommended).

#### Execute — CLI (Primary)
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{user.ns}}","MetricName":"{{user.metric}}"},"Stat":"Average","Period":3600}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)", "Label":"7-Day Forecast"}
  ]' \
  --start-time $(date -d '-14 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.get_metric_data(
    MetricDataQueries=[
        {'Id': 'm1', 'MetricStat': {'Metric': {'Namespace': '{{user.ns}}', 'MetricName': '{{user.metric}}'}, 'Stat': 'Average', 'Period': 3600}},
        {'Id': 'fc', 'Expression': 'FORECAST(m1, "linear", 168)', 'Label': '7-Day Forecast'}
    ],
    StartTime=datetime.utcnow() - timedelta(days=14),
    EndTime=datetime.utcnow()
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Check `.MetricDataResults[]` contains both actual and forecast results.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix forecast model/period; retry once |
| ThrottlingException | Backoff; retry 3x |

### Operation: Logs Insights (Start Query)

#### Execute — CLI (Primary)
```bash
aws logs start-query \
  --log-group-names "{{user.log}}" \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /(?i)(error|exception|fail)/ | stats count() by bin(5m) | limit 20' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
logs = boto3.client('logs', region_name='{{user.region}}')
start_response = logs.start_query(
    logGroupNames=['{{user.log}}'],
    startTime=int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
    endTime=int(datetime.utcnow().timestamp()),
    queryString='fields @timestamp, @message | filter @message like /(?i)(error|exception|fail)/ | stats count() by bin(5m)'
)
query_id = start_response['queryId']
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
Poll `aws logs get-query-results --query-id "{{output.qid}}"` until status is `Complete` (max 5 min timeout). Check `.results` is non-empty.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix query string; retry once |
| MalformedQueryException | HALT — fix query syntax |
| ThrottlingException | Backoff; retry 3x |

### Operation: Contributor Insights (Put Insight Rule)

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-insight-rule \
  --rule-name "{{user.alarm}}" \
  --rule-state ENABLED \
  --rule-definition '{
    "Schema": {"Name": "CloudWatchLogRule", "Version": 1},
    "AggregateOn": "Count",
    "Contribution": {
      "Keys": ["$.userIdentity.arn"],
      "Filters": [{"Match": "$.errorCode", "Comparison": "starts-with", "Value": "Access"}]
    },
    "LogGroupNames": ["{{user.log}}"]
  }' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_insight_rule(
    RuleName='{{user.alarm}}',
    RuleState='ENABLED',
    RuleDefinition={
        'Schema': {'Name': 'CloudWatchLogRule', 'Version': 1},
        'AggregateOn': 'Count',
        'Contribution': {
            'Keys': ['$.userIdentity.arn'],
            'Filters': [{'Match': '$.errorCode', 'Comparison': 'starts-with', 'Value': 'Access'}]
        },
        'LogGroupNames': ['{{user.log}}']
    }
)
```

#### Validate
`aws cloudwatch list-insight-rules --region "{{user.region}}"` → confirm rule exists and `State` is `ENABLED`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix definition; retry once |
| LimitExceeded | HALT — delete unused rules |
| ThrottlingException | Backoff; retry 3x |

### Operation: Delete Insight Rule

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Execute — CLI (Primary)
```bash
aws cloudwatch delete-insight-rules --rule-names "{{user.alarm}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_insight_rules(RuleNames=['{{user.alarm}}'])
```

#### Validate
`aws cloudwatch list-insight-rules` → rule no longer listed.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — rule doesn't exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Create Dashboard

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-dashboard \
  --dashboard-name "{{user.dash}}" \
  --dashboard-body '{"widgets":[{"type":"metric","properties":{"metrics":[["{{user.ns}}","{{user.metric}}"]],"period":300,"stat":"Average"}}]}' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
dashboard_body = {"widgets": [{"type": "metric", "properties": {"metrics": [["{{user.ns}}", "{{user.metric}}"]], "period": 300, "stat": "Average"}}]}
client.put_dashboard(DashboardName='{{user.dash}}', DashboardBody=json.dumps(dashboard_body))
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
`aws cloudwatch list-dashboards --region "{{user.region}}"` → dashboard exists.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix dashboard body; retry once |
| LimitExceeded | HALT — delete unused dashboards |
| ThrottlingException | Backoff; retry 3x |

### Operation: Delete Dashboard

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Pre-flight
Verify dashboard exists:
```bash
aws cloudwatch get-dashboard --dashboard-name "{{user.dash}}" --region "{{user.region}}" --output json
```

#### Execute — CLI (Primary)
```bash
aws cloudwatch delete-dashboards --dashboard-names "{{user.dash}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_dashboards(DashboardNames=['{{user.dash}}'])
```

#### Validate
`aws cloudwatch list-dashboards --region "{{user.region}}"` → dashboard absent.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFound | HALT — dashboard does not exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Set Log Retention Policy

**Safety Gate**: MUST obtain explicit user confirmation (permanent data loss).

#### Execute — CLI (Primary)
```bash
aws logs put-retention-policy \
  --log-group-name "{{user.log}}" \
  --retention-in-days 30 \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_retention_policy(
    logGroupName='{{user.log}}',
    retentionInDays=30
)
```

#### Validate
`aws logs describe-log-groups --log-group-name-prefix "{{user.log}}"` → confirm `retentionInDays` matches.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix retention days; retry once |
| ResourceNotFoundException | HALT — log group doesn't exist |
| ThrottlingException | Backoff; retry 3x |

### Operation: Synthetics Canary (Create)

#### Pre-flight
Verify canary name not taken:
```bash
aws synthetics describe-canaries --region "{{user.region}}" --query "Canaries[?Name=='{{user.canary}}']" --output json
```

#### Execute — CLI (Primary)
```bash
aws synthetics create-canary \
  --name "{{user.canary}}" \
  --artifact-s3-location "s3://{{user.bucket}}/canary-artifacts/" \
  --execution-role-arn "{{user.role_arn}}" \
  --schedule expression="rate(5 minutes)" \
  --runtime-version syn-nodejs-puppeteer-9.1 \
  --code '{"Handler":"canary.handler","Script":"const synthetics = require(\"Synthetics\"); exports.handler = async () => { await synthetics.executeStep(\"heartbeat\", async () => { await synthetics.getPage(); }); };"}' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.create_canary(
    Name='{{user.canary}}',
    ArtifactS3Location='s3://{{user.bucket}}/canary-artifacts/',
    ExecutionRoleArn='{{user.role_arn}}',
    Schedule={'Expression': 'rate(5 minutes)'},
    RuntimeVersion='syn-nodejs-puppeteer-9.1',
    Code={'Handler': 'canary.handler', 'Script': 'const synthetics = require("Synthetics"); exports.handler = async () => { await synthetics.executeStep("heartbeat", async () => { await synthetics.getPage(); }); };'}
)
```

#### Validate
`aws synthetics describe-canaries --names "{{user.canary}}"` → `Status.State=RUNNING`.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix canary config; retry once |
| ConflictException | HALT — canary name already exists |
| ThrottlingException | Backoff; retry 3x |

### Operation: Synthetics Canary (Delete)

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Execute — CLI (Primary)
```bash
aws synthetics delete-canary --name "{{user.canary}}" --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_canary(Name='{{user.canary}}')
```

#### Validate
`aws synthetics describe-canaries --names "{{user.canary}}"` → canary not found.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | HALT — canary doesn't exist |
| ConflictException | HALT — canary still running; stop first |
| ThrottlingException | Backoff; retry 3x |

### Operation: Diagnose Alarm

#### Execute — CLI (Primary)
```bash
# Describe alarm state
aws cloudwatch describe-alarms --alarm-names "{{user.alarm}}" --region "{{user.region}}" --output json

# Describe alarm history
aws cloudwatch describe-alarm-history --alarm-name "{{user.alarm}}" --region "{{user.region}}" --output json

# Get associated metric data
aws cloudwatch get-metric-statistics --namespace "{{user.ns}}" --metric-name "{{user.metric}}" \
  --statistics Average --period 300 \
  --start-time $(date -d '-1 hour' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region "{{user.region}}" --output json
```

#### Execute — boto3 (Fallback)
```python
alarm = client.describe_alarms(AlarmNames=['{{user.alarm}}'])
history = client.describe_alarm_history(AlarmName='{{user.alarm}}')
```
See `references/troubleshooting.md` for diagnosis procedures.

#### Validate
Cross-reference alarm state, history, and raw metric data to identify root cause.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFound | HALT — alarm not found |
| ThrottlingException | Backoff; retry 3x |

## AIOps Cross-Cutting Operations

### Cost Anomaly RCA

#### Execute — CLI (Primary)
```bash
# Query billing metrics
aws cloudwatch get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges \
  --statistics Maximum --period 86400 \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region us-east-1 --output json
```

Cross-reference billing spikes with resource metrics (EC2 CPU, Lambda Invocations, DynamoDB capacity). Recommend downsize, cleanup, or right-size. See [references/core-concepts.md §FinOps](references/core-concepts.md#finops-cost-management).

### Predictive Maintenance (FORECAST)

See `### Operation: FORECAST Metric Trend` above. If projected to exceed safe threshold within 7 days → alert → recommend scale-up. Under-utilization trend → recommend downsize. Orchestrator intent: `capacity-forecast`. See [references/elb-monitoring-templates.md §FORECAST](references/elb-monitoring-templates.md#forecast--elb-capacity-planning).

### Certificate Expiry (Custom Metric)

Delegate cert discovery to `aws-acm-ops`; publish days-to-expiry as custom metric:

```bash
aws cloudwatch put-metric-data \
  --namespace AWS/AIOps \
  --metric-data '[{"MetricName":"CertDaysToExpiry","Dimensions":[{"Name":"Domain","Value":"{{domain}}"}],"Value":{{days}},"Unit":"Count"}]' \
  --region {{user.region}} --output json

aws cloudwatch put-metric-alarm \
  --alarm-name "{{domain}}-Cert-Expiry" \
  --namespace AWS/AIOps \
  --metric-name CertDaysToExpiry \
  --dimensions Name=Domain,Value={{domain}} \
  --statistic Minimum --period 86400 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "{{sns_arn}}" \
  --region {{user.region}} --output json
```

### Three-Layer Inspection

CloudWatch correlates metrics across layers. Bottom-up chain:

```
Network Layer     ← aws-elb-ops + aws-vpc-ops
Resource Layer    ← aws-ec2-ops + aws-rds-ops + aws-aurora-ops + aws-elasticache-ops + aws-dynamodb-ops
Application Layer ← aws-eks-ops
```

Output format: [references/layered-inspection-template.md](references/layered-inspection-template.md).

### Auto-Heal Feedback Loop

Persist heal outcomes for MTTR tracking:

```bash
aws logs put-log-events \
  --log-group-name /aws/aiops/feedback/elb \
  --log-stream-name auto-heal \
  --log-events timestamp=$(date +%s000),message='{"scenario":"AH-01","success":true,"mttr_seconds":270}'
```

Full schema and query patterns: [references/feedback-loop.md](references/feedback-loop.md).

### ELB Alarm Templates & AIOps Dashboard

Delegates ELB ARN discovery to `aws-elb-ops`, then creates alarms and the AIOps dashboard. See [references/elb-monitoring-templates.md](references/elb-monitoring-templates.md) for:

- Anomaly Detection — ALB Request Count
- Latency Alarm (p99)
- UnHealthyHostCount Alarm
- 5xx Error Rate Alarm
- ELB Capacity Planning (FORECAST)
- AIOps Dashboard via [assets/elb-aiops-dashboard.json](assets/elb-aiops-dashboard.json)

## Token Efficiency Guidelines (P0)

The following 6 rules minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding metric or operator tables.
```markdown
# DO: list-metrics to discover
aws cloudwatch list-metrics --namespace "{{user.ns}}" --region "{{user.region}}" --output json
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def create_alarm(client, name):
    try: return client.put_metric_alarm(AlarmName=name)
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| InvalidParameterValue | HALT — fix params |
```
### TE-4: Centralized JSON paths
File-top `## Common JSON Paths` block; one path per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&defaults` anchors in `assets/example-config.yaml`.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in reference files.

## Safety Gates

| Operation | Safety Gate |
|-----------|-------------|
| Delete Alarm | **Human confirm** `DELETE_ALARMS <names>` — verify names and impact |
| Delete Insight Rule | **Human confirm** — verify rule name and impact |
| Delete Dashboard | **Human confirm** `DELETE_DASHBOARD <name>` — verify dashboard name |
| Set Log Retention | **Human confirm** — permanent data loss, verify retention days |
| Synthetics Canary (Delete) | **Human confirm** — verify canary name and impact |

## Reference Files

- [Prompt Examples](references/prompt-examples.md) — user scenarios
- [Operation Index](references/operation-index.md) — full routing table
- [AWS CLI Usage](references/aws-cli-usage.md) — CLI commands and patterns
- [boto3 SDK Usage](references/boto3-sdk-usage.md) — SDK code examples
- [Core Concepts](references/core-concepts.md) — CloudWatch architecture and FinOps
- [Troubleshooting](references/troubleshooting.md) — error codes and diagnosis
- [GCL Rubric](references/rubric.md) — scoring criteria
- [GCL Prompt Templates](references/prompt-templates.md) — G/C/O skeletons
- [ELB Monitoring Templates](references/elb-monitoring-templates.md) — ELB-specific alarms
- [AIOps Scenarios](references/aiops-scenarios.md) — cost RCA, FORECAST, cert expiry
- [Feedback Loop](references/feedback-loop.md) — auto-heal tracking
- [Layered Inspection](references/layered-inspection-template.md) — full-stack inspection
- [ELB AIOps Dashboard](assets/elb-aiops-dashboard.json) — 8-widget dashboard

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `recommended` |
| `max_iterations` | `3` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` |
| Trace | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops need trace confirmation: `delete-alarms`, `delete-insight-rules`, `delete-dashboards`, `delete-canary`, `put-retention-policy`. Rules A7–A10: `aws-skill-generator/references/gcl-spec.md` §8.

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md). Parse `aiops_delegate:` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope`, `trace_id`). Writes: idempotency_key (24h dedup); destructive ops need `confirmation_token`; respect decision tier; propagate `trace_id` in User-Agent; always emit `aiops_context:` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).