# AIOps Feedback Loop — Auto-Heal Success Tracking

_Lastest update: 2026-05-31_

This document defines how to persist auto-heal action results for continuous improvement.

---

## Feedback Data Model

Each auto-heal action records a structured event:

```json
{
  "timestamp": "2026-05-31T10:23:00Z",
  "scenario": "AH-01",
  "trigger": "UnHealthyHostCount > 0",
  "target_resource": "arn:aws:elasticloadbalancing:...:targetgroup/web/xxx",
  "target_id": "i-xxx",
  "rca_result": "CPU 95% - capacity saturation",
  "decision": "[AUTO_HEAL]",
  "action": "deregister -> 30s wait -> re-register",
  "success": true,
  "mttr_seconds": 270,
  "retry_count": 0,
  "region": "us-east-1"
}
```

## Storage: CloudWatch Logs (Zero Setup)

```bash
# Publish feedback event to CloudWatch Logs
aws logs put-log-events \
  --log-group-name /aws/aiops/feedback/elb \
  --log-stream-name auto-heal \
  --log-events timestamp=$(date +%s000),message='{"scenario":"AH-01","success":true,"mttr_seconds":270}'
```

## Query: Success Rate Over Time

```bash
aws logs start-query \
  --log-group-name /aws/aiops/feedback/elb \
  --query-string 'fields @timestamp, scenario, success, mttr_seconds
    | stats avg(mttr_seconds) as avg_mttr, sum(success) as total_success, count(*) as total
    by scenario
    | sort total desc'
```

## Query: Trending MTTR Over Time

```bash
aws logs start-query \
  --log-group-name /aws/aiops/feedback/elb \
  --query-string 'fields @timestamp, scenario, success, mttr_seconds
    | filter scenario = "AH-01"
    | stats avg(mttr_seconds) by bin(1d)'
```

## Dashboard: Auto-Heal Performance

```json
{
  "type": "log",
  "properties": {
    "query": "SOURCE '/aws/aiops/feedback/elb' | stats count(*) as total, sum(success) as success by scenario | sort total desc",
    "region": "us-east-1",
    "title": "Auto-Heal Success Rate by Scenario"
  }
}
```

## Continuous Improvement Rules

| Observation | Action |
|------------|--------|
| AH-01 success rate < 80% | Review AH-01 parameters; increase wait time |
| MTTR increasing > 10% week-over-week | Investigate systemic latency |
| Same target fails auto-heal > 3x | Escalate to MANUAL; mark target for replacement |
| New scenario has < 10 samples | Run in AI_ASSIST mode until enough data |

## Integration: Auto-Export to S3 for Analysis

```bash
aws logs put-subscription-filter \
  --log-group-name /aws/aiops/feedback/elb \
  --filter-name aiops-feedback-export \
  --filter-pattern '' \
  --destination-arn arn:aws:firehose:region:account:deliverystream/aiops-feedback
```