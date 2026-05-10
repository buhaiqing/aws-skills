# AWS CloudFront Ops Skill

AWS CloudFront operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests distribution creation or deletion
- User needs to manage cache behaviors
- User asks about CloudFront
- User mentions "CDN", "distribution", "origin", "cache"
- User needs to invalidate cached content
- User asks about SSL/TLS certificates for CloudFront
- User needs to configure custom domains

**SHOULD-NOT activate when:**
- S3 bucket operations only (use `aws-s3-ops`)
- ELB operations (use `aws-elb-ops`)
- Route53 operations (use `aws-route53-ops`)

**Delegation:**
- S3 → `aws-s3-ops` (origin bucket)
- Route53 → `aws-route53-ops` (DNS/alias records)
- ACM → `aws-acm-ops` (SSL/TLS certificates)
- Lambda → `aws-lambda-ops` (Lambda@Edge)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Distribution | Yes | None |
| Update Distribution | Yes | None |
| Disable Distribution | Yes | None |
| Delete Distribution | Yes | **Human confirmation** |
| Create CloudFront Origin Access Identity | Yes | None |
| Create Cache Invalidation | Yes | None |
| Get Distribution Status | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.DistributionId}}` | User input | E1234567890ABC |
| `{{user.Domain}}` | User input | example.com |
| `{{user.OriginDomain}}` | User input | mybucket.s3.amazonaws.com |
| `{{user.AcmCertArn}}` | User input | arn:aws:acm:us-east-1:... |

## Execution Flow

### Pre-flight
```
1. Check AWS CLI: aws --version
2. Validate credentials: aws sts get-caller-identity
3. Verify origin exists (S3/ELB/custom origin)
4. Check SSL certificate in us-east-1
```

### Execute (Primary: CLI)
```
aws cloudfront create-distribution \
  --distribution-config file://distribution-config.json \
  --output json
```

### Execute (Fallback: boto3)
```python
import boto3
cf = boto3.client('cloudfront')
response = cf.create_distribution(
    DistributionConfig={...}
)
```

## Safety Gates

### Distribution Deletion
```
BEFORE delete-distribution:
1. Disable distribution first
2. Wait for disabled state
3. Ask: "Type 'DELETE {{user.DistributionId}}' to confirm"
```

## Output Convention

Key JSON paths:
- `.Distribution.Id` - distribution ID
- `.Distribution.DomainName` - CloudFront domain
- `.Distribution.Status` - Deployed/InProgress
- `.DistributionConfig.Enabled` - true/false
- `.DistributionConfig.DefaultCacheBehavior` - cache config
- `.Invalidation.Id` - invalidation ID

## Related Skills

- `aws-s3-ops` - S3 origin bucket
- `aws-route53-ops` - DNS alias
- `aws-acm-ops` - SSL/TLS certificates

## Reference Files

- `references/aws-cli-usage.md`
- `references/boto3-sdk-usage.md`
- `references/core-concepts.md`
- `references/troubleshooting.md`
- `assets/example-config.yaml`