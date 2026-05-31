# Route53 Skill — AIOps Prompt Examples

_Lastest update: 2026-05-31_

---

## Scenario 1: DNS failover when ALB is unhealthy

### User Prompt
```
My primary ALB is down. Fail over to the backup.
```

### Agent Execution
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify primary unhealthy | `aws cloudwatch get-metric-statistics HealthyHostCount` | |
| 2. Check failover record exists | `aws route53 list-resource-record-sets` | |
| 3. Swap DNS weight | primary=0 secondary=100 | `[AUTO_HEAL]` |
| 4. Verify propagation | `dig {{record}} +short` | |

```bash
aws route53 change-resource-record-sets --hosted-zone-id {{zone}} --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"{{record}}","Type":"A","SetIdentifier":"secondary","Failover":"SECONDARY","Weight":100}}]}'
```

---

## Scenario 2: Health check failing for LB endpoint

### User Prompt
```
Route53 health check for my ALB is failing. What's wrong?
```

### Agent Execution
```bash
aws route53 get-health-check --health-check-id {{hc_id}}
aws elbv2 describe-target-health --target-group-arn {{tg_arn}}
curl -I http://{{lb_dns}}:{{port}}/{{path}}
```

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "Primary ALB down, fail over" | DNS failover | `[AUTO_HEAL]` | r53 + elb |
| "Health check failing" | HC RCA | `[AI_ASSIST]` | r53 + elb |
| "DNS not resolving after change" | Propagation check | `[AI_ASSIST]` | r53 |
