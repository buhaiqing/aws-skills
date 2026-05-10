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