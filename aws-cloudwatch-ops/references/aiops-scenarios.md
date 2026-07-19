# AIOps Cross-Cutting Scenarios — CloudWatch

_Latest update: 2026-06-13_

Orchestrator-facing scenarios where CloudWatch is the observability hub. Delegate resource ops to domain skills; use this skill for metrics, logs, alarms, and FORECAST.

> **Bidirectional link**: [SKILL.md](../SKILL.md) → `## Scope` · [operation-index.md](operation-index.md)

---

## Cost Anomaly RCA

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Billing --metric-name EstimatedCharges \
  --statistics Maximum --period 86400 \
  --start-time $(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z) --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region us-east-1 --output json
```

Cross-reference billing spikes with resource metrics (EC2 CPU, Lambda Invocations, DynamoDB capacity). Recommend downsize, cleanup, or right-size. FinOps pricing: [core-concepts.md §FinOps](core-concepts.md#finops-cost-management).

## Predictive Maintenance (FORECAST)

1. Query `FORECAST(m, model, periods)` via `get-metric-data`
2. If projected to exceed safe threshold within 7 days → alert → recommend scale-up
3. Under-utilization trend → recommend downsize

Orchestrator intent: `capacity-forecast`. ELB example: [elb-monitoring-templates.md §FORECAST](elb-monitoring-templates.md#forecast--elb-capacity-planning).

## Certificate Expiry (Custom Metric)

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

## Three-Layer Inspection

CloudWatch correlates metrics across layers. Bottom-up chain:

```
Network Layer     ← aws-elb-ops + aws-vpc-ops
Resource Layer    ← aws-ec2-ops + aws-rds-ops + aws-aurora-ops + aws-elasticache-ops + aws-dynamodb-ops
Application Layer ← aws-eks-ops
```

Trigger phrases:
> "帮我做一次全面运维巡检，包含根因分析和自治愈建议"
> "Run a full-stack inspection with root cause analysis and auto-healing recommendations"

Output format: [layered-inspection-template.md](layered-inspection-template.md).

## Auto-Heal Feedback Loop

Persist heal outcomes for MTTR tracking:

```bash
aws logs put-log-events \
  --log-group-name /aws/aiops/feedback/elb \
  --log-stream-name auto-heal \
  --log-events timestamp=$(date +%s000),message='{"scenario":"AH-01","success":true,"mttr_seconds":270}'
```

Full schema and query patterns: [feedback-loop.md](feedback-loop.md).

## ELB Alarm Templates & AIOps Dashboard

Delegates ELB ARN discovery to `aws-elb-ops`, then creates alarms and the AIOps dashboard. See [elb-monitoring-templates.md](elb-monitoring-templates.md) for:

- Anomaly Detection — ALB Request Count
- Latency Alarm (p99)
- UnHealthyHostCount Alarm
- 5xx Error Rate Alarm
- ELB Capacity Planning (FORECAST)
- AIOps Dashboard via [assets/elb-aiops-dashboard.json](../assets/elb-aiops-dashboard.json)

## Common Pre-flight Steps (all ops)

### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

### Step 2: Load & Verify Credentials
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
Action: See troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws cloudwatch list-metrics --region {{user.region}}` | Suggest valid region |
