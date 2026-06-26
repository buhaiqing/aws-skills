# VPC Skill — AIOps Prompt Examples

## Scenario 1: LB Connection Timeout — Network RCA
**User**: "Users are reporting connection timeouts through the NLB. Is it a network problem?"

| Step | Action | Delegate |
|------|--------|----------|
| 1. NAT Gateway check | `get-metric-statistics ActiveConnectionCount PacketsDropCount` | aws-vpc-ops |
| 2. Flow Log analysis | Query REJECT records | aws-vpc-ops |
| 3. SG changes | `cloudtrail lookup-events SecurityGroup` | aws-cloudtrail-ops |
| 4. Target port check | `nc -zv {{target}} {{port}}` | aws-ec2-ops |

```bash
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name PacketsDropCount --statistics Sum --period 300
```

## Scenario 2: Security Group Audit
**User**: "Check if any security groups changed recently that could affect my ALB health checks."

```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress --start-time "$(date -d '-24 hours' -u ...)"
```

## Quick Reference
| User says | Scenario | Tier | Modules |
|-----------|----------|------|---------|
| "NLB connection timeout" | NAT/Flow Log RCA | AI_ASSIST | vpc + ec2 + ct |
| "SG changed affecting health check" | SG drift | MANUAL | vpc + ct |
| "Check network path from LB to target" | Reachability Analyzer | AI_ASSIST | vpc |