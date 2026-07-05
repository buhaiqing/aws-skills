# Route53 Troubleshooting

## Error Code Reference

### Hosted Zone Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **NoSuchHostedZone** | Zone deleted or wrong ID | `list-hosted-zones` → verify | [→](troubleshooting-details/zone-errors.md) |
| **HostedZoneAlreadyExists** | Zone name exists | Use existing zone or different name | - |

### Record Set Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **InvalidChangeBatch** | Record syntax or invalid values | Check name format, IPs, TTL | [→](troubleshooting-details/record-errors.md) |
| **PriorRequestNotComplete** | Previous change in progress | Wait, then `get-change` for status | [→](troubleshooting-details/record-errors.md) |

### Health Check Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| **NoSuchHealthCheck** | Deleted or wrong ID | `list-health-checks` |
| **HealthCheckAlreadyExists** | Same caller reference used | Use unique caller reference (e.g., UUID) |

## Common Issues

### DNS Not Resolving

| Symptom | Diagnosis | Resolution | Details |
|---------|-----------|------------|---------|
| NXDOMAIN / site unreachable | `dig NS {{zone}} +short` → check NS match registrar | Wait for propagation, check record name | [→](troubleshooting-details/dns-resolution.md) |

### Health Check Failing

| Symptom | Diagnosis | Common Causes |
|---------|-----------|---------------|
| Status Unhealthy | `get-health-check`, test endpoint with `curl -I` | Endpoint down, SG blocking HC IPs, SSL expired, non-200 response |

**Detailed:** [Health Check](troubleshooting-details/health-checks.md)

### Failover Not Working

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Traffic not switching | `list-resource-record-sets` → check `Failover` config | Ensure HC associated, `EvaluateTargetHealth=true` for alias |

**Detailed:** [Failover](troubleshooting-details/failover.md)

## Recovery Flow

| Category | Steps |
|----------|-------|
| Zone | Check exists → verify NS match registrar → wait for propagation |
| Record | Check records → validate syntax → `test-dns-answer` → wait INSYNC → `dig` verify |
| Health Check | Check endpoint → verify SGs → review config → monitor status |

## Monitoring Checklist

| Check | Warning | Critical | Action |
|-------|---------|----------|--------|
| Health Check Status | Unhealthy | Persistent | Check endpoint |
| DNS Query Rate | > 1000/min | > 10000/min | Review traffic |
| Change Status | PENDING > 5 min | PENDING > 30 min | Contact AWS |
| Record Count | > 8000 | > 9500 | Request increase |

## AIOps: DNS Failover Automation

### AH-R53-01: ELB Health-Based DNS Failover [AUTO_HEAL]

Trigger: `aws-elb-ops` detects `HealthyHostCount = 0` for all target groups.

```
1. get-health-check-status → verify HC
2. list-resource-record-sets → identify primary/secondary
3. Swap weights: primary=0, secondary=100
4. get-change → wait INSYNC → dig verify
5. Notify: "DNS failover activated"
```

**Boundary**: Only if `EvaluateTargetHealth=true` AND secondary LB exists.
**Cross-module**: `aws-elb-ops` (target health), `aws-cloudwatch-ops` (metrics), `aws-acm-ops` (SSL).

### Health Check RCA for ELB

```
1. get-health-check → check config
2. elbv2 describe-target-health → check LB targets
3. curl endpoint manually
4. Check SG allows Route53 health check IPs
5. → LB targets healthy but HC failing = SG blocking
   → LB targets unhealthy = ELB issue
   → Endpoint non-200 = application issue
```

### DNS Propagation Monitoring

```bash
for ns in $(dig NS {{zone_name}} +short); do dig @$ns {{record_name}} A +short; done
aws route53 test-dns-answer --hosted-zone-id {{zone_id}} --record-name {{record_name}} --record-type A
```