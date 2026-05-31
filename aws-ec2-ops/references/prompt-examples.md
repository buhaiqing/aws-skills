# EC2 Skill — AIOps Prompt Examples

_Lastest update: 2026-05-31_

This document provides concrete user prompts for EC2-LB integration diagnostics and auto-healing.

---

## Scenario 1: EC2 instance behind LB is unhealthy

### User Prompt
```
I have an EC2 instance i-xxx that my ALB keeps marking as unhealthy. Can you check and fix it?
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Check instance status | `aws ec2 describe-instance-status --instance-ids i-xxx` | |
| 2. Check CPU trend (30 min) | `aws cloudwatch get-metric-statistics CPUUtilization` | |
| 3. Check CloudTrail for changes | `aws cloudtrail lookup-events` | |
| 4. CPU > 90% or StatusCheck failed | | `[AUTO_HEAL]` reboot |
| 5. Verify recovery | Poll StatusCheck until ok | |

```bash
aws ec2 reboot-instances --instance-ids i-xxx
```

---

## Scenario 2: CPU capacity forecast

### User Prompt
```
My EC2 instance CPU is rising. Will it hit 100% soon?
```

### Agent Execution
```bash
aws cloudwatch get-metric-data --metric-data-queries '[
  {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization"},"Period":3600,"Stat":"Average"}},
  {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day"}
]'
```

Output:
```
Current: 72% | 7d forecast: 88% | 14d forecast: 95%
Action: [AI_ASSIST] Resize t3.medium -> t3.large recommended
```

---

## Scenario 3: Application not responding on LB

### User Prompt
```
My LB health check is failing. Can you run SSM diagnostics on the target instance to find out why?
```

### Agent Execution
```bash
aws ssm send-command --instance-ids {{instance_id}} \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["ss -tlnp", "systemctl status nginx", "df -h", "free -m"]}'
```

Output: Port 80 not listening → `[AI_ASSIST] restart application`

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "Instance keeps going unhealthy in LB" | EC2 diagnostics + reboot | `[AUTO_HEAL]` | ec2 + elb |
| "CPU is rising, will it hit 100%" | Capacity FORECAST | `[AI_ASSIST]` | ec2 + cw |
| "Health check fails, run SSM check" | SSM diagnostics | `[AI_ASSIST]` | ec2 + ssm |
