# Route53 Failover Issues — Detailed Recovery

## Diagnosis

```bash
aws route53 list-resource-record-sets --hosted-zone-id {{zone_id}} \
  --query "ResourceRecordSets[?Name=='{{name}}']"
```

## Resolution

1. Ensure health check is associated with record
2. Check failover configuration (PRIMARY vs SECONDARY)
3. Verify EvaluateTargetHealth is true for alias records
4. Wait for DNS propagation

## AIOps: DNS Failover Automation

**AH-R53-01: ELB Health-Based DNS Failover [AUTO_HEAL]**

Trigger: aws-elb-ops detects HealthyHostCount = 0 for all target groups.

1. get-health-check-status → verify health check
2. list-resource-record-sets → identify primary/secondary records
3. Swap weights: primary=0, secondary=100
4. get-change → wait INSYNC → dig verify
5. Notify: "DNS failover activated"

Boundary: Only if EvaluateTargetHealth=true AND secondary LB exists.

## Cross-Module Integration

| Condition | Delegate To |
|-----------|-------------|
| Primary health check failure | aws-elb-ops (target health) |
| Failover decision | aws-cloudwatch-ops (HealthyHostCount) |
| HTTPS certificate | aws-acm-ops (SSL check) |
| Secondary LB missing | aws-elb-ops (create ALB) |