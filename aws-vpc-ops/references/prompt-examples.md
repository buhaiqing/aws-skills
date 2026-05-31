# VPC Skill — AIOps Prompt Examples

_Lastest update: 2026-05-31_

---

## Scenario 1: LB connection timeout — network RCA

### User Prompt
```
Users are reporting connection timeouts through the NLB. Is it a network problem?
```

### Agent Execution
| Step | Action | Delegate |
|------|--------|----------|
| 1. Check NAT Gateway | `get-metric-statistics ActiveConnectionCount PacketsDropCount` | aws-vpc-ops |
| 2. VPC Flow Log analysis | Query REJECT records | aws-vpc-ops |
| 3. Check SG changes | `cloudtrail lookup-events SecurityGroup` | aws-cloudtrail-ops |
| 4. Target port check | `nc -zv {{target}} {{port}}` | aws-ec2-ops |

```bash
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name PacketsDropCount --statistics Sum --period 300
```

---

## Scenario 2: Security group audit

### User Prompt
```
Check if any security groups changed recently that could affect my ALB health checks.
```

### Agent Execution
```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress --start-time "$(date -d '-24 hours' -u ...)"
```

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "NLB connection timeout" | NAT/Flow Log RCA | `[AI_ASSIST]` | vpc + ec2 + ct |
| "SG changed affecting health check" | SG drift detection | `[MANUAL]` | vpc + ct |
| "Check network path from LB to target" | Reachability Analyzer | `[AI_ASSIST]` | vpc |
