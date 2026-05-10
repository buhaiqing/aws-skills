# Core Concepts — S3

## What is Amazon S3

- **Purpose**: Object storage with scalability, availability, and security
- **Category**: Storage
- **Console**: https://console.aws.amazon.com/s3/
- **Docs**: https://docs.aws.amazon.com/s3/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Bucket | Storage container | /s3/home?region=us-east-1#/buckets |
| Object | File stored in bucket | Bucket → Objects tab |
| Prefix | Folder-like path | Object key path |
| Version | Object version (if enabled) | Bucket → Properties → Versioning |

## Storage Classes

| Class | Use Case | Cost | Access |
|-------|----------|------|--------|
| STANDARD | General purpose | Higher | Immediate |
| STANDARD_IA | Infrequent access | Lower | Immediate |
| ONEZONE_IA | Infrequent, single AZ | Lowest IA | Immediate |
| GLACIER | Archive | Low | Minutes-hours |
| DEEP_ARCHIVE | Long archive | Lowest | Hours |
| INTELLIGENT_TIERING | Auto optimization | Medium | Immediate |

## Bucket Naming Rules

- 3-63 characters
- Lowercase letters, numbers, hyphens, periods
- Must start with letter or number
- No uppercase
- No underscore
- No consecutive periods
- Cannot be IP address format (e.g., 192.168.1.1)
- Global namespace (unique across all AWS accounts)

## Quotas

| Quota | Default | Adjustable |
|-------|---------|------------|
| Buckets per account | 100 | Yes (up to 1000 via support) |
| Objects per bucket | Unlimited | No |
| Object size max | 5TB | No |
| Multipart upload parts max | 10,000 | No |
| List operations (requests/sec) | 100-800 | No |

## Object Limits

| Limit | Value |
|-------|-------|
| Maximum object size | 5TB |
| Minimum object size | 0 bytes |
| Multipart upload threshold | 100MB (recommended) |
| Minimum multipart part size | 5MB |
| Maximum multipart part size | 5GB |

## Lifecycle States

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Active | Normal state | All operations |
| Archived | Glacier storage | Restore before access |
| Transitioning | Moving between classes | Limited |
| Deleted | Removed | N/A |

## Dependencies

| Dependency | Required | Skill |
|------------|----------|-------|
| IAM Policy | Yes | `aws-iam-ops` |
| VPC Endpoint (optional) | No | `aws-vpc-ops` |
| KMS Key (encryption) | Optional | `aws-kms-ops` |
| SNS Topic (notifications) | Optional | `aws-sns-ops` |

## Region Handling

S3 buckets are regional but namespace is global:
- `us-east-1`: No LocationConstraint needed for create
- Other regions: Must specify LocationConstraint
- Buckets accessible from any region after creation

## Pricing Model

- **Storage**: Per GB/month per class
- **Requests**: PUT/GET/LIST per 1000 requests
- **Data transfer**: Outbound per GB
- **Free tier**: 5GB storage, 20,000 GET, 2,000 PUT for 12 months

## Best Practices

### Security
- Block public access by default
- Enable bucket policy for access control
- Use SSE-S3, SSE-KMS, or SSE-C encryption
- Enable MFA delete for sensitive buckets
- Enable object lock for compliance

### Availability
- Use multiple AZs (default)
- Cross-region replication for DR
- Versioning for protection

### Cost
- Lifecycle policies to transition/archive
- Intelligent-tiering for variable access
- Delete incomplete multipart uploads