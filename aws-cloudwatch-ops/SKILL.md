---
name: aws-cloudwatch-ops
description: >-
  Use when operating AWS CloudWatch alarms, metrics, and dashboards via AWS CLI
  or boto3 SDK; user mentions CloudWatch, CW, metrics, alarms, monitoring, or
  dashboards.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to CloudWatch endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS CloudWatch Operations Skill

## Overview

Amazon CloudWatch provides monitoring for AWS resources and applications via metrics, alarms, logs, and dashboards. This skill is an **operational runbook** for CloudWatch operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "CloudWatch", "CW", "metrics", "alarms", "monitoring"
- Task involves **metrics, alarms, dashboards, or log groups**
- Keywords: alarm, metric, dashboard, threshold, namespace, dimension

### SHOULD NOT Use When
- EC2 instance ops → delegate to: `aws-ec2-ops`
- S3 bucket ops → delegate to: `aws-s3-ops`
- RDS database ops → delegate to: `aws-rds-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use `us-east-1` if unset |
| `{{user.alarm_name}}` | User input | Ask once; reuse |
| `{{user.namespace}}` | User input | Ask once; reuse |
| `{{output.alarm_arn}}` | Last API response | Parse: `.AlarmArn` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

### Operation: Create Alarm

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; configure credentials |
| Metric exists | `aws cloudwatch list-metrics` | Suggest valid namespace/metric |
| Threshold valid | Validate comparison operator | Suggest valid values |

#### Execute — CLI (Primary)
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "{{user.alarm_name}}" \
  --metric-name "{{user.metric_name}}" \
  --namespace "{{user.namespace}}" \
  --statistic "{{user.statistic}}" \
  --period {{user.period}} \
  --threshold {{user.threshold}} \
  --comparison-operator "{{user.comparison_operator}}" \
  --evaluation-periods {{user.evaluation_periods}} \
  --alarm-actions "{{user.alarm_actions}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('cloudwatch', region_name='{{user.region}}')
response = client.put_metric_alarm(
    AlarmName='{{user.alarm_name}}',
    MetricName='{{user.metric_name}}',
    Namespace='{{user.namespace}}',
    Statistic='{{user.statistic}}',
    Period={{user.period}},
    Threshold={{user.threshold}},
    ComparisonOperator='{{user.comparison_operator}}',
    EvaluationPeriods={{user.evaluation_periods}},
    AlarmActions=['{{user.alarm_actions}}']
)
```

#### Validate
```bash
aws cloudwatch describe-alarms --alarm-names "{{user.alarm_name}}" --region "{{user.region}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameterValue | Fix threshold/operator; retry once |
| ResourceNotFound | Verify namespace/metric exists |
| Throttling (429) | Backoff, retry 3x |

### Operation: Delete Alarm (Destructive)

**Safety Gate**: MUST obtain explicit confirmation.
> "Delete alarm {{user.alarm_name}}? This is IRREVERSIBLE."

#### Execute — CLI
```bash
aws cloudwatch delete-alarms --alarm-names "{{user.alarm_name}}" --region "{{user.region}}" --output json
```

### Operation: Get Metric Data

#### Execute — CLI
```bash
aws cloudwatch get-metric-data \
  --metric-data-queries '[{"Id":"m1","MetricStat":{"Metric":{"Namespace":"{{user.namespace}}","MetricName":"{{user.metric_name}}"},"Stat":"{{user.statistic}}","Period":{{user.period}}}}]' \
  --start-time "{{user.start_time}}" \
  --end-time "{{user.end_time}}" \
  --region "{{user.region}}" \
  --output json
```

### Operation: List Metrics

#### Execute — CLI
```bash
aws cloudwatch list-metrics \
  --namespace "{{user.namespace}}" \
  --region "{{user.region}}" \
  --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| MetricName | `.Metrics[].MetricName` | Metric identifier |
| Namespace | `.Metrics[].Namespace` | Service namespace |
| Dimensions | `.Metrics[].Dimensions[]` | Resource filters |

## Common Namespace-Metric Patterns

| Service | Namespace | Key Metrics |
|---------|-----------|-------------|
| EC2 | AWS/EC2 | CPUUtilization, NetworkIn/Out |
| S3 | AWS/S3 | BucketSizeBytes, NumberOfObjects |
| RDS | AWS/RDS | CPUUtilization, FreeStorageSpace |
| Lambda | AWS/Lambda | Invocations, Errors, Duration |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)