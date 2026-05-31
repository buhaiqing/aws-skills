# Route53 Troubleshooting

Common Route53 error codes, recovery procedures, and operational troubleshooting.

## Error Code Reference

### Hosted Zone Errors

#### NoSuchHostedZone
```
Error: Hosted zone {{zone_id}} does not exist
```
**Cause**: Zone deleted or incorrect ID.
**Resolution**:
```bash
# List zones
aws route53 list-hosted-zones --output json

# Check zone exists
aws route53 get-hosted-zone --id {{zone_id}}
```

#### HostedZoneAlreadyExists
```
Error: Hosted zone {{zone_name}} already exists
```
**Cause**: Zone with this name already created.
**Resolution**: Use existing zone or different name.

### Record Set Errors

#### InvalidChangeBatch
```
Error: Invalid change batch
```
**Cause**: Record syntax error or invalid values.
**Resolution**:
- Check record name format
- Verify IP addresses are valid
- Ensure CNAME values are hostnames
- Check TTL values (positive integer)

#### PriorRequestNotComplete
```
Error: Another change is in progress
```
**Cause**: Previous change not yet synced.
**Resolution**:
```bash
# Wait and retry
# Check change status
aws route53 get-change --id {{change_id}}
```

### Health Check Errors

#### NoSuchHealthCheck
```
Error: Health check {{check_id}} does not exist
```
**Cause**: Health check deleted or wrong ID.
**Resolution**:
```bash
# List health checks
aws route53 list-health-checks --output json
```

#### HealthCheckAlreadyExists
```
Error: Health check with caller reference exists
```
**Cause**: Same caller reference used.
**Resolution**: Use unique caller reference (e.g., UUID).

## Common Issues

### DNS Not Resolving

#### Symptoms
- `dig` or `nslookup` returns NXDOMAIN
- Website not accessible

#### Diagnosis
```bash
# Check name servers
dig NS {{zone_name}} +short

# Query specific nameserver
dig @{{name_server}} {{record_name}} +short

# Check TTL
dig {{record_name}} +noall +answer
```

#### Resolution
1. Verify record exists: `aws route53 list-resource-record-sets`
2. Check name servers match domain registrar
3. Wait for DNS propagation (TTL period)
4. Check for typos in record name

### Health Check Failing

#### Symptoms
- Health check status: Unhealthy
- Failover not working

#### Diagnosis
```bash
# Check health check status
aws route53 get-health-check --health-check-id {{check_id}}

# Test endpoint manually
curl -I http://{{endpoint}}/{{path}}
```

#### Common Causes
- Endpoint down
- Security group blocking health check IPs
- SSL certificate expired
- Path returns non-200 status

#### Resolution
1. Verify endpoint is accessible
2. Check security groups allow Route53 health check IPs
3. Ensure HTTP response code is 200
4. Review CloudWatch logs for errors

### Failover Not Working

#### Symptoms
- Traffic not switching to secondary
- Health check shows unhealthy but traffic continues

#### Diagnosis
```bash
# Check record set with failover
aws route53 list-resource-record-sets \
  --hosted-zone-id {{zone_id}} \
  --query "ResourceRecordSets[?Name=='{{name}}']"

# Verify health check association
```

#### Resolution
1. Ensure health check is associated with record
2. Check failover configuration (PRIMARY vs SECONDARY)
3. Verify EvaluateTargetHealth is true for alias records
4. Wait for DNS propagation

## Recovery Procedures

### Zone Recovery Flow
```
1. Check zone exists with get-hosted-zone
2. For deletion: confirm no critical records
3. For creation: verify zone name unique
4. Update registrar with correct name servers
5. Wait for propagation
```

### Record Recovery Flow
```
1. Check current records with list-resource-record-sets
2. Validate record syntax
3. Test with test-dns-answer API
4. Apply change and wait for INSYNC
5. Verify with dig/nslookup
```

### Health Check Recovery Flow
```
1. Check endpoint accessibility
2. Verify security groups
3. Review health check configuration
4. Update if needed
5. Monitor status changes
```

## Monitoring Checklist

| Check | Warning | Critical | Action |
|-------|---------|----------|--------|
| Health Check Status | Unhealthy | Persistent failures | Check endpoint |
| DNS Query Rate | > 1000/min | > 10000/min | Review traffic |
| Change Status | PENDING > 5 min | PENDING > 30 min | Contact AWS |
| Record Count | > 8000 | > 9500 | Request increase |

## AIOps: DNS Failover Automation

### AH-R53-01: ELB Health-Based DNS Failover [AUTO_HEAL]

When ELB reports all targets unhealthy, trigger DNS failover to secondary LB:

```
Trigger: aws-elb-ops detects HealthyHostCount = 0 for all target groups
┌───────────────────────────────────────────────────────────────────┐
│ Step 1 — Verify health check status                               │
│ aws route53 get-health-check-status --health-check-id {{hc_id}}   │
│                                                                   │
│ Step 2 — Identify primary and secondary records                  │
│ aws route53 list-resource-record-sets --hosted-zone-id {{zone}}   │
│   --query "ResourceRecordSets[?Failover != null]"                  │
│                                                                   │
│ Step 3 — Execute failover                                         │
│ # Swap weights: primary=0, secondary=100                          │
│ aws route53 change-resource-record-sets ... (see SKILL.md)        │
│                                                                   │
│ Step 4 — Validate                                                 │
│ aws route53 get-change --id {{change_id}}                         │
│ # Wait for INSYNC                                                 │
│ dig {{record_name}} +short  # Should return secondary LB IP       │
│                                                                   │
│ Step 5 — Notify                                                   │
│ "DNS failover activated: primary LB unhealthy, traffic redirected │
│  to secondary LB. Monitor and revert once primary recovers."      │
└───────────────────────────────────────────────────────────────────┘
```

**Decision**: `[AUTO_HEAL]`
**Boundary**: Only if `EvaluateTargetHealth=true` AND secondary LB exists.
**Rollback**: Swap weights back when primary recovers.

### Health Check RCA for ELB Integration

```
Trigger: Route53 health check shows unhealthy for LB endpoint
┌───────────────────────────────────────────────────────────────────┐
│ Step 1 — Check health check config                                │
│ aws route53 get-health-check --health-check-id {{hc_id}}          │
│                                                                   │
│ Step 2 — Check ELB target health (delegate aws-elb-ops)          │
│ aws elbv2 describe-target-health --target-group-arn {{tg_arn}}    │
│                                                                   │
│ Step 3 — Check endpoint manually                                  │
│ # From Route53 health checker perspective                         │
│ curl -I http://{{lb_dns_name}}:{{port}}/{{path}}                  │
│                                                                   │
│ Step 4 — Check SG allows Route53 IPs                              │
│ # Route53 health check IP ranges: https://ip-ranges.amazonaws.com │
│                                                                   │
│ Step 5 — Action                                                   │
│ → LB targets healthy but HC failing → SG blocking Route53 IPs    │
│ → LB targets unhealthy → ELB-level issue (delegate to elb-ops)   │
│ → Endpoint returns non-200 → Application issue                    │
└───────────────────────────────────────────────────────────────────┘
```

### DNS Propagation Monitoring

```bash
# After DNS change, monitor propagation across global resolvers
for ns in $(dig NS {{zone_name}} +short); do
  echo "Nameserver: $ns"
  dig @$ns {{record_name}} A +short
done

# Or use Route53 test-dns-answer
aws route53 test-dns-answer \
  --hosted-zone-id {{zone_id}} \
  --record-name {{record_name}} \
  --record-type A
```

### Cross-Module Integration for Failover

| Condition | Delegate To |
|-----------|-------------|
| Primary health check failure | `aws-elb-ops` (check target health) |
| Failover decision based on LB metrics | `aws-cloudwatch-ops` (HealthyHostCount) |
| Certificate validation for HTTPS | `aws-acm-ops` (SSL check) |
| Secondary LB creation if missing | `aws-elb-ops` (create secondary ALB) |