# AWS CloudTrail Ops Skill

AWS CloudTrail operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests CloudTrail trail creation, modification, or deletion
- User asks to query events with `lookup-events`
- User needs to enable/disable trail logging
- User mentions "CloudTrail", "audit trail", "API logging", "event history"
- User needs to troubleshoot "who did what when" in AWS
- User asks about CloudTrail Insights or anomaly detection
- User needs multi-region or organization trail setup

**SHOULD-NOT activate when:**
- General monitoring/alarms (use `aws-cloudwatch-ops`)
- S3 bucket operations (use `aws-s3-ops`)
- IAM operations (use `aws-iam-ops`)
- Log analysis (use `aws-cloudwatch-ops`)

**Delegation:**
- S3 bucket → `aws-s3-ops` (trail logging bucket)
- KMS key → `aws-kms-ops` (trail encryption)
- CloudWatch Logs → `aws-cloudwatch-ops` (CloudWatch integration)
- IAM → `aws-iam-ops` (trail role permissions)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Trail | Yes | S3 bucket policy check |
| Describe Trails | Yes | None |
| Get Trail Status | Yes | None |
| Update Trail | Yes | None |
| Delete Trail | Yes | **Human confirmation** |
| Start Logging | Yes | None |
| Stop Logging | Yes | None |
| Lookup Events | Yes | Pagination required |
| Get Event Selectors | Yes | None |
| Put Event Selectors | Yes | None |
| Get Insights Selectors | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.TrailName}}` | User input | management-trail |
| `{{user.S3BucketName}}` | User input | my-cloudtrail-logs |
| `{{user.S3KeyPrefix}}` | User input | audit/ |
| `{{user.KmsKeyId}}` | User input | alias/cloudtrail |
| `{{user.StartTime}}` | User input | 2024-01-01T00:00:00Z |
| `{{user.EndTime}}` | User input | 2024-01-15T23:59:59Z |

**Never commit real credentials. Always use `{{env.*}}` or `{{user.*}}` placeholders.**

## Execution Flow

### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

```
3. Confirm region: aws cloudtrail describe-trails --region {{env.AWS_DEFAULT_REGION}}
4. Verify S3 bucket exists: aws s3 ls s3://{{user.S3BucketName}}/
5. Check bucket policy: aws s3api get-bucket-policy --bucket {{user.S3BucketName}}
```

### Execute (Primary: CLI)
```
aws cloudtrail create-trail \
  --name {{user.TrailName}} \
  --s3-bucket-name {{user.S3BucketName}} \
  --s3-key-prefix {{user.S3KeyPrefix}} \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --kms-key-id {{user.KmsKeyId}} \
  --is-organization-trail \
  --output json
```

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK:
```python
import boto3
cloudtrail = boto3.client('cloudtrail', region_name='{{env.AWS_DEFAULT_REGION}}')
response = cloudtrail.create_trail(
    Name='{{user.TrailName}}',
    S3BucketName='{{user.S3BucketName}}',
    IsMultiRegionTrail=True,
    EnableLogFileValidation=True
)
```

### Validate
```
1. Poll status: aws cloudtrail get-trail-status --name {{user.TrailName}}
2. Wait for IsLogging: true
3. Max wait: 5 minutes
4. Validate S3 delivery
```

### Recover
| Error Type | Action |
|------------|---------|
| TrailAlreadyExists | HALT - provide existing trail info |
| TrailNotFound | HALT - verify trail name |
| InsufficientS3BucketPolicy | FIX - update bucket policy |
| InvalidCloudWatchLogsLogGroup | FIX - verify log group exists |
| KMSKeyNotFound | FIX - verify KMS key exists |
| S3BucketNotFound | FIX - create bucket first |
| Throttling | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Trail Deletion (Critical)
```
BEFORE delete-trail:
1. Display: "Deleting {{user.TrailName}} will stop all audit logging"
2. Ask: "Type 'DELETE {{user.TrailName}}' to confirm"
3. Human must type exact confirmation string
4. Proceed only after confirmation matches
```

### Stop Logging
```
BEFORE stop-logging:
1. Warn: "Logging will stop. No events will be recorded"
2. Ask: "Continue? (yes/no)"
3. Require explicit "yes"
```

## Output Convention

Always use `--output json` for agent parsing.

Key JSON paths:
- `.Trail.Name` - trail name
- `.Trail.S3BucketName` - S3 bucket
- `.Trail.IsMultiRegionTrail` - boolean
- `.Trail.IsOrganizationTrail` - boolean
- `.TrailStatus.IsLogging` - boolean
- `.TrailStatus.StartLoggingTime` - timestamp
- `.TrailStatus.LatestDeliveryError` - delivery error message
- `.Events[]` - event list
- `.Events[].EventId` - unique event ID
- `.Events[].EventTime` - event timestamp
- `.Events[].EventSource` - service that generated event
- `.Events[].Username` - IAM user/role that made the call
- `.Events[].CloudTrailEvent` - full event JSON

## Related Skills

- `aws-s3-ops` - S3 bucket for trail logs
- `aws-kms-ops` - KMS key for trail encryption
- `aws-iam-ops` - IAM roles for CloudTrail access
- `aws-cloudwatch-ops` - CloudWatch Logs integration
- `aws-organizations-ops` - Organization trails

## Reference Files

- `references/aws-cli-usage.md` - CLI command reference
- `references/boto3-sdk-usage.md` - Python SDK patterns
- `references/core-concepts.md` - CloudTrail architecture
- `references/troubleshooting.md` - Error codes, recovery
- `assets/example-config.yaml` - Trail configuration