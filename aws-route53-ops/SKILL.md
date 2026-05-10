# AWS Route53 Ops Skill

AWS Route53 DNS operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests DNS record creation, modification, or deletion
- User needs to configure health checks
- User asks about Route53 failover routing
- User mentions "Route53", "DNS", "hosted zone", "record set"
- User needs to troubleshoot DNS resolution issues
- User asks about latency-based routing or geolocation routing
- User needs to configure alias records for AWS resources

**SHOULD-NOT activate when:**
- Domain registration only (use AWS Console)
- Certificate validation (use `aws-acm-ops`)
- Load balancer configuration (use `aws-elb-ops`)

**Delegation:**
- ELB health checks → `aws-elb-ops` (target group health)
- CloudWatch alarms → `aws-cloudwatch-ops` (health check monitoring)
- S3 static hosting → `aws-s3-ops` (website endpoints)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Hosted Zone | Yes | None |
| Delete Hosted Zone | Yes | **Human confirmation** |
| Create Record Set | Yes | None |
| Update Record Set | Yes | None |
| Delete Record Set | Yes | **Human confirmation** |
| Create Health Check | Yes | None |
| Update Health Check | Yes | None |
| Delete Health Check | Yes | None |
| Test DNS Answer | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.ZoneId}}` | User input | Z1234567890ABC |
| `{{user.ZoneName}}` | User input | example.com |
| `{{user.RecordName}}` | User input | www.example.com |
| `{{user.RecordType}}` | User input | A, AAAA, CNAME, MX, TXT |
| `{{user.HealthCheckId}}` | User input | 12345678-abcd-1234-abcd-123456789012 |

## Execution Flow

### Pre-flight
```
1. Check AWS CLI availability: aws --version
2. Validate credentials: aws sts get-caller-identity
3. Confirm hosted zone exists: aws route53 get-hosted-zone --id {{user.ZoneId}}
4. Check service quotas: aws service-quotas get-service-quota --service-code route53 --quota-code L-...
```

### Execute (Primary: CLI)
```
aws route53 change-resource-record-sets \
  --hosted-zone-id {{user.ZoneId}} \
  --change-batch file://change-batch.json \
  --output json
```

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK:
```python
import boto3
route53 = boto3.client('route53', region_name='{{env.AWS_DEFAULT_REGION}}')
response = route53.change_resource_record_sets(
    HostedZoneId='{{user.ZoneId}}',
    ChangeBatch={'Changes': [...]}
)
```

### Validate
```
1. Query DNS: dig {{user.RecordName}} +short
2. Check record set: aws route53 list-resource-record-sets --hosted-zone-id {{user.ZoneId}}
3. Max wait: 60 seconds (DNS propagation)
```

### Recover
| Error Type | Action |
|------------|---------|
| NoSuchHostedZone | HALT - zone does not exist |
| InvalidChangeBatch | FIX - check record set syntax |
| PriorRequestNotComplete | RETRY - wait for previous change |
| Throttling (429) | Exponential backoff; max 3 retries |

## Safety Gates

### Record Set Deletion
```
BEFORE delete-resource-record-sets:
1. Display: "Deleting record set {{user.RecordName}} will stop DNS resolution"
2. Ask: "Type 'DELETE {{user.RecordName}}' to confirm"
3. Proceed only after confirmation matches
```

## Output Convention

Always use `--output json` for agent parsing.

Key JSON paths:
- `.ChangeInfo.Id` - change request ID
- `.ChangeInfo.Status` - PENDING, INSYNC
- `.HostedZone.Id` - hosted zone ID
- `.HostedZone.Name` - zone name
- `.ResourceRecordSets[].Name` - record name
- `.ResourceRecordSets[].Type` - record type
- `.ResourceRecordSets[].TTL` - time to live
- `.HealthCheck.Id` - health check ID
- `.HealthCheck.HealthCheckConfig.*` - health check config

## Related Skills

- `aws-elb-ops` - Health check target groups
- `aws-cloudwatch-ops` - Health check monitoring
- `aws-s3-ops` - Static website endpoints
- `aws-cloudfront-ops` - CloudFront alias records

## Reference Files

- `references/aws-cli-usage.md` - CLI command reference
- `references/boto3-sdk-usage.md` - Python SDK patterns
- `references/core-concepts.md` - DNS architecture, routing policies
- `references/troubleshooting.md` - Error codes, recovery procedures
- `assets/example-config.yaml` - Configuration examples