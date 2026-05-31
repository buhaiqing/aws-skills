---
name: aws-route53-ops
description: >-
  Use when the user needs to create, manage, or delete DNS records and hosted
  zones in AWS Route53; configure DNS routing policies including failover,
  latency-based, geolocation, or weighted routing for Route53 hosted zones; set
  up health checks for DNS failover; manage alias records pointing to AWS
  resources like ELB, S3, or CloudFront; troubleshoot DNS resolution issues;
  or delegate domain zones in Route53, even if they don't say "Route53" and
  instead say "set up DNS records", "configure DNS failover", "manage hosted
  zones", "set up health checks for my website", or "create alias records
  for AWS resources".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Route53 endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-05-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
  cross_skill_deps:
    - aws-elb-ops             # ELB health-based DNS failover
    - aws-cloudwatch-ops      # Health check monitoring
    - aws-acm-ops              # DNS validation for certificates
    - aws-cloudfront-ops      # CloudFront alias records
---
# AWS Route53 Ops Skill

AWS Route53 DNS operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create Zone:     .HostedZone.Id  (strip "/hostedzone/" prefix)
#                  .DelegationSet.NameServers[]
# List Zones:      .HostedZones[].{Id,Name,ResourceRecordSetCount}
# Change Record:   .ChangeInfo.{Id,Status}
# List Records:    .ResourceRecordSets[].{Name,Type,TTL,ResourceRecords}
# Create HC:       .HealthCheck.Id
# Test DNS:        .TestResult
```

## Trigger & Scope

### SHOULD Use When
- User requests DNS record creation, modification, or deletion
- User needs to configure health checks
- User asks about Route53 failover routing
- User mentions "Route53", "DNS", "hosted zone", "record set"
- User needs to troubleshoot DNS resolution issues
- User asks about latency-based or geolocation routing
- User needs to configure alias records for AWS resources
- **(AIOps)** DNS failover automation for ELB health-based routing
- **(AIOps)** Route53 health check integration with ELB target health
- **(AIOps)** DNS propagation monitoring after LB or ELB changes
- **(AIOps)** Auto-failover when ELB targets are unhealthy
- Keywords: failover, dns-health, elb-dns, dns-failover, route53-healthcheck

### SHOULD NOT Use When
- Domain registration only (use AWS Console)
- Certificate validation → delegate to: `aws-acm-ops`
- Load balancer configuration → delegate to: `aws-elb-ops`

### Delegation
- CloudWatch alarms → `aws-cloudwatch-ops` (health check monitoring)
- S3 static hosting → `aws-s3-ops` (website endpoints)

## Scope & Quick Reference

| Operation | CLI | Safety Gate |
|-----------|-----|-------------|
| Create Hosted Zone | `aws route53 create-hosted-zone --name {{u.name}}` | None |
| Delete Hosted Zone | `aws route53 delete-hosted-zone --id {{u.id}}` | **Human confirmation** |
| Create/Update Record | `aws route53 change-resource-record-sets --hosted-zone-id {{u.id}} --change-batch file://batch.json` | None |
| Delete Record Set | Same as above with Action=DELETE | **Human confirmation** |
| Create Health Check | `aws route53 create-health-check --caller-reference {{u.ref}} --health-check-config file://hc.json` | None |
| Update/Delete HC | `aws route53 update-health-check / delete-health-check` | None |
| Test DNS Answer | `aws route53 test-dns-answer --hosted-zone-id {{u.id}} --record-name {{u.name}} --record-type {{u.type}}` | None |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temporary credentials |
| `{{user.ZoneId}}` | User input | Ask once; reuse |
| `{{user.ZoneName}}` | User input | example.com |
| `{{user.RecordName}}` | User input | www.example.com |
| `{{user.RecordType}}` | User input | A, AAAA, CNAME, MX, TXT |
| `{{user.RecordValue}}` | User input | IP or target DNS name |
| `{{user.HealthCheckId}}` | User input | UUID format |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify hosted zone exists via `get-hosted-zone`. Check quotas via `service-quotas`.

**CLI (primary)**: `aws route53 [command] --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Query DNS via `dig` or `test-dns-answer`. Max wait 60s for propagation. Use `get-change --id {{o.ChangeId}}` to poll PENDING→INSYNC.

**Common Recovery**:
| Error | Action |
|-------|--------|
| NoSuchHostedZone | HALT — zone does not exist |
| InvalidChangeBatch | FIX — check record set syntax |
| PriorRequestNotComplete | RETRY — wait for previous change |
| Throttling (429) | Exponential backoff; max 3 retries |

## Safety Gates

### Record Set Deletion
```
⚠️ Deleting record {{user.RecordName}} will stop DNS resolution.
Confirm: Type DELETE {{user.RecordName}} to proceed.
```

### Hosted Zone Deletion
```
⚠️ Zone must be empty (no record sets) before deletion.
Confirm: Type DELETE {{user.ZoneName}} to proceed.
```

## Related Skills

- `aws-elb-ops` — Health check target groups
- `aws-cloudwatch-ops` — Health check monitoring
- `aws-s3-ops` — Static website endpoints
- `aws-cloudfront-ops` — CloudFront alias records

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)

---

## AIOps: DNS Routing Automation for ELB Failover

### AIOps Data Collection

| Data Source | AIOps Use |
|-------------|-----------|
| Route53 Health Check Status | ELB health-based DNS failover detection |
| CloudWatch `HealthCheckStatus` | Health check status monitoring |
| CloudTrail `ChangeResourceRecordSets` | DNS change detection and rollback |
| ELB `HealthyHostCount` | Trigger DNS failover when targets are unhealthy |

### Auto-Failover with Route53 Health Checks

DNS failover architecture:
```
User → Route53 Alias Record
         ├── Primary (weight=100) → ALB-A (us-east-1a)
         │    └── Health Check → ALB-A's Target Group health
         │
         └── Secondary (weight=0) → ALB-B (us-east-1b)  [activated on failover]
              └── Health Check → ALB-B's Target Group health
```

#### AH-R53-01: Automated DNS Failover [AUTO_HEAL]

When ELB health check detects all targets in one AZ are unhealthy:

```bash
# 1. Verify health check exists for this LB
aws route53 list-health-checks \
  --query "HealthChecks[?HealthCheckConfig.FullyQualifiedDomainName.contains(@, '{{lb_dns_name}}')]"

# 2. Update failover record
# Change primary weight to 0, secondary weight to 100
aws route53 change-resource-record-sets \
  --hosted-zone-id {{zone_id}} \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "{{record_name}}",
          "Type": "A",
          "SetIdentifier": "primary",
          "Failover": "PRIMARY",
          "Weight": 0,
          "AliasTarget": {
            "DNSName": "{{primary_lb_dns}}",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "{{record_name}}",
          "Type": "A",
          "SetIdentifier": "secondary",
          "Failover": "SECONDARY",
          "Weight": 100,
          "AliasTarget": {
            "DNSName": "{{secondary_lb_dns}}",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

**Decision**: `[AUTO_HEAL]` (reversible, no data loss).
**Fallback**: If no secondary LB exists → `[AI_ASSIST]` inform user.

### Cross-Module Integration

| Condition | Delegate To |
|-----------|-------------|
| ELB health check state | `aws-elb-ops` (target group health) |
| DNS change monitoring | `aws-cloudwatch-ops` (alarms on DNS changes) |
| Health check status | `aws-cloudwatch-ops` (HealthCheckStatus metric) |
| SSL certificate for DNS | `aws-acm-ops` (cert validation) |