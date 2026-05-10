# CloudTrail Core Concepts

AWS CloudTrail architecture, components, and operational concepts.

## Service Overview

**AWS CloudTrail** - AWS account activity logging service that records API calls and other activity in AWS infrastructure.

**Key Benefits:**
- Security analysis and compliance auditing
- Operational troubleshooting (who did what when)
- Visibility into user and resource activity
- Event history for up to 90 days (lookup-events API)
- Long-term log retention in S3
- Real-time monitoring via CloudWatch Logs
- Event-driven automation via SNS/SQS

## Trail Types

### Management Trails
**Characteristics:**
- Record management events
- Include control plane operations
- Free for first management trail per region
- Additional trails charged

**Management Events Include:**
- IAM policy changes
- VPC configuration changes
- EC2 instance creation/deletion
- S3 bucket policy changes
- RDS database operations
- Lambda function configuration
- KMS key management

### Data Events
**Characteristics:**
- Record data plane operations on resources
- Charged separately ($0.10 per 100,000 events)
- Must be explicitly configured

**Data Events Include:**
- S3 object-level operations (PutObject, GetObject, etc.)
- Lambda function invocations
- DynamoDB item-level operations (table-level only in CloudTrail)

**Note:** DynamoDB item-level data events require separate configuration via CloudTrail event selectors.

## Trail Configuration

### Single-Region Trail
- **Scope**: Records events only in one region
- **Use Case**: Region-specific compliance requirements
- **Cost**: Lower (single region S3 storage)
- **Limitations**: Misses cross-region activities

### Multi-Region Trail
- **Scope**: Records events across all enabled regions
- **Use Case**: Global compliance, security monitoring
- **Cost**: Higher (multi-region S3 storage, replication)
- **Benefits**: Complete visibility, automatic region coverage

### Organization Trail
- **Scope**: Records events from all member accounts
- **Requirements**: AWS Organizations, management account
- **Use Case**: Centralized security auditing for enterprise
- **Benefits**: Single trail for entire organization
- **Setup**: Created from management account

## Event Types

### Management Events

**Control Plane Operations:**
- Create, delete, modify AWS resources
- IAM authentication and authorization
- API calls to AWS services

**Subtypes:**
- **Read-only**: Get*, List*, Describe* (view resource)
- **Write-only**: Create*, Delete*, Modify*, Put* (change resource)
- **All**: Both read and write operations

**Free Tier:**
- First management trail per region: Free
- Additional trails: Charged
- Data events: Always charged

### Data Events

**S3 Data Events:**
- Object-level operations
- GetObject, PutObject, DeleteObject
- ListObjects (bucket-level)
- Object ACL changes

**Lambda Data Events:**
- Function invocations (Invoke)
- Event source mappings

**Configuration:**
- Must specify resource ARNs or use wildcards
- Can use `*` for all resources of type
- Example: `arn:aws:s3:::bucket/*` for all objects

## Event Selectors

### Purpose
Control which events are logged to trail.

### Types

#### Management Event Selectors
```
IncludeManagementEvents: true/false
ReadWriteType: All | ReadOnly | WriteOnly
```

#### Data Event Selectors
```
Type: AWS::S3::Object | AWS::Lambda::Function
Values: [ARN patterns]
```

### Best Practices
- Use `ReadWriteType: All` for comprehensive logging
- Enable management events (free for first trail)
- Selectively enable data events (charged)
- Use specific ARNs for data events, not wildcards
- Separate high-volume S3 buckets from others

## CloudTrail Insights

### Purpose
Automatically detect unusual API activity patterns.

### Insight Types

#### API Call Rate Insights
- Detects unusual volume of API calls
- Baseline established over 7 days
- Alerts on significant deviations

#### API Error Rate Insights
- Detects unusual error patterns
- Helps identify misconfigurations or attacks
- Baseline established over 7 days

### Configuration
- Must enable Insights on trail
- Separate cost for Insights events
- Delivered to same S3 bucket as regular events

## Log File Characteristics

### Delivery
- **Frequency**: Within 15 minutes of API call
- **Format**: JSON
- **Compression**: GZIP
- **Naming**: `YYYY/MM/DD/HH/account-id_CloudTrail_region-name_YYYYMMDDTHHmmZ_unique-string.json.gz`

### Contents
Each log file contains:
- Multiple event records
- Standardized event structure
- Request and response details
- User identity information
- Source IP and user agent
- Error information (if any)

### Validation
**Log File Validation:**
- Cryptographically signs log files
- Detects log file tampering
- Uses digest files
- Digest delivered every hour

## Integration Points

### S3 Integration
**Delivery:**
- Log files delivered to S3 bucket
- Requires bucket policy allowing CloudTrail write
- Supports SSE-S3 or SSE-KMS encryption

**Bucket Policy Requirements:**
- `s3:GetBucketAcl` for validation
- `s3:PutObject` for log delivery
- `s3:x-amz-acl` condition for ownership

### CloudWatch Logs Integration
**Purpose:**
- Real-time log processing
- Metric filters and alarms
- Search and analysis
- Longer retention

**Configuration:**
- Requires CloudWatch Logs log group
- Requires IAM role with permissions
- Log stream per CloudTrail log file

### SNS Notification
**Purpose:**
- Real-time event notification
- Trigger automated responses
- Integration with SIEM/SOC

**Delivery:**
- Sent for each log file delivery
- Contains S3 object key
- Can trigger Lambda functions

### EventBridge Integration
**Purpose:**
- Event-driven automation
- Real-time response to API calls
- Complex event processing

**Use Cases:**
- Auto-remediation of misconfigurations
- Security incident response
- Compliance violation detection

## Security Features

### Encryption
**At Rest:**
- S3 SSE-S3 (default)
- S3 SSE-KMS (customer-managed key)
- KMS key per trail or shared

**In Transit:**
- TLS 1.2+ for all CloudTrail APIs
- HTTPS for S3 delivery

### Log File Integrity
**Digest Files:**
- Cryptographic hash chain
- Signed with CloudTrail private key
- Verifiable by CloudTrail CLI/SDK
- Tamper detection

**Verification:**
```bash
aws cloudtrail validate-logs \
  --trail-arn {{trail_arn}} \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z
```

### Access Control
**IAM Permissions:**
- `cloudtrail:CreateTrail`
- `cloudtrail:DescribeTrails`
- `cloudtrail:GetTrailStatus`
- `cloudtrail:LookupEvents`
- `s3:*` (for S3 bucket)
- `logs:*` (for CloudWatch Logs)
- `kms:*` (for SSE-KMS)

**Best Practices:**
- Least privilege access
- Separate CloudTrail admin role
- Monitor CloudTrail configuration changes
- Use SCPs for Organizations

## Quotas (Service Limits)

| Quota | Default Limit | Notes |
|-------|---------------|-------|
| Trails per region | 5 | Can request increase |
| Event selectors per trail | 5 | - |
| LookupEvents API | 2 TPS | Throttled after |
| Data events | No limit | Charged per event |
| Event history | 90 days | Stored by AWS |
| Log file delivery | 15 min | Typical latency |

## Cost Components

### Management Trails
- **First per region**: Free
- **Additional trails**: $2.00 per 100,000 events

### Data Events
- **S3**: $0.10 per 100,000 events
- **Lambda**: $0.10 per 100,000 events
- **DynamoDB**: $0.10 per 100,000 events

### Insights Events
- $0.35 per 100,000 events
- Separate from management/data events

### S3 Storage
- Standard S3 storage costs
- Lifecycle policies for cost optimization
- Glacier for long-term retention

### CloudWatch Logs
- Log ingestion charges
- Log storage charges
- Custom metrics (if used)

## Best Practices

### Security
- Enable log file validation
- Use SSE-KMS with customer-managed key
- Create multi-region trail for global visibility
- Use Organization trail for enterprise
- Enable Insights for anomaly detection

### Compliance
- Retain logs per compliance requirements
- Use S3 Object Lock for immutability
- Enable MFA Delete on S3 bucket
- Monitor trail configuration changes
- Regular log file validation

### Operations
- Use specific event selectors, not wildcards
- Monitor data event costs
- Set up CloudWatch Logs for real-time analysis
- Configure SNS for critical event notifications
- Automate response via EventBridge

### Cost Optimization
- Use first management trail (free)
- Selectively enable data events
- Use S3 lifecycle policies
- Archive old logs to Glacier
- Monitor Insights costs

## Common Patterns

### Security Monitoring Trail
- Multi-region
- All management events
- Data events for sensitive S3 buckets
- CloudWatch Logs for real-time
- SNS for SIEM integration
- Insights enabled

### Compliance Trail
- Multi-region or organization
- All management events
- S3 with Object Lock
- Long retention (7 years)
- Regular validation

### Cost-Optimized Trail
- First trail only (free tier)
- Write-only management events
- No data events
- S3 lifecycle to Glacier
- No CloudWatch Logs

### Audit Investigation
- Use lookup-events API
- Query 90-day history
- Parse S3 log files for older events
- Use Athena for SQL queries
- Correlate with CloudWatch Logs