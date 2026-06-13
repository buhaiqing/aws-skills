---
runbook_id: "02"
scenario: "Emergency troubleshoot"
version: "1.0.0"
last_updated: "2026-06-13"
trigger: "Alarm / user report"
risk_level: "high"
execution_time_estimate: "3-8 min"
---

> **Script**: [`runbooks/scripts/emergency-troubleshoot.py`](../scripts/emergency-troubleshoot.py)

# Emergency Troubleshoot

## 1. Purpose

Fast chain RCA when users report outage or alarms fire (5xx, latency, connection errors). Narrow time window (last 1h), prioritize ELB target health + EC2 status + RDS connections.

## 2. Pre-flight

Same as [01-daily-health-check.md](01-daily-health-check.md) plus symptom capture:

- `{{user.symptom}}` — e.g. `502`, `timeout`, `slow`
- `{{user.primary_resource}}` — optional ALB ARN or instance ID

## 3. Execution

### Phase 1 — Symptom anchor (60 min)

```bash
aws elbv2 describe-target-health \
  --target-group-arn "$TG_ARN" --output json

aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=app/... \
  --start-time "$START" --end-time "$END" \
  --period 60 --statistics Sum --output json
```

### Phase 2 — Parallel deep collect

- EC2: `StatusCheckFailed`, CPU, recent `aws ec2 describe-instance-status`
- RDS: `DatabaseConnections`, `ReadLatency`/`WriteLatency`
- VPC: SG rules on instance ENI (`aws ec2 describe-network-interfaces`)
- CloudTrail: `aws cloudtrail lookup-events` last 1h on in-scope ARNs

### Phase 3 — Top-3 hypotheses

Map to inference rules: `ALB-EC2-01`, `RDS-CONN-01`, `NAT-PORT-01`, etc.

## 4. Run

```bash
python3 runbooks/scripts/emergency-troubleshoot.py \
  --resource-group prod-web-rg \
  --symptom 502 \
  --region us-east-1
```

## 5. Escalation

If ≥ 3 CRITICAL incidents → delegate enriched RCA to `aws-aiops-orchestrator` with `action_mode=recommend`.
