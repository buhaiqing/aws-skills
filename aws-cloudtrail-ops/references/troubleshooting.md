# CloudTrail Troubleshooting

Common CloudTrail error codes, recovery procedures, and operational troubleshooting.

## Error Code Reference

### Trail Errors

#### TrailAlreadyExists
```
Error: Trail {{trail_name}} already exists
```
**Cause**: Attempting to create trail with existing name in region.
**Resolution**:
```bash
# Check existing trails
aws cloudtrail describe-trails --trail-name-list {{trail_name}}

# Use different name or update existing
current_name=$(aws cloudtrail describe-trails \
  --query "trailList[?Name=='{{trail_name}}'].Name" \
  --output text)
  
if [ -n "$current_name" ]; then
  echo "Trail exists. Use update-trail or different name."
fi
```

#### TrailNotFound
```
Error: Trail {{trail_name}} not found
```
**Cause**: Trail deleted, wrong name, or wrong region.
**Resolution**:
```bash
# List all trails
aws cloudtrail describe-trails --output json

# Check specific region
aws cloudtrail describe-trails \
  --trail-name-list {{trail_name}} \
  --region {{region}} \
  --output json

# Trail might be in different home region
trails=$(aws cloudtrail describe-trails \
  --query "trailList[?Name=='{{trail_name}}']" \
  --output json)
```

#### TrailNotProvided
```
Error: Trail name must be specified
```
**Cause**: Required trail name parameter missing.
**Resolution**: Always specify `--name` or `--trail-name-list` parameter.

#### InvalidTrailName
```
Error: Trail name must be 3-128 characters
```
**Cause**: Trail name doesn't meet naming requirements.
**Resolution**:
- 3-128 characters
- Alphanumeric and underscores, hyphens, periods only
- No spaces
- Unique per region

### S3 Bucket Errors

#### S3BucketNotFound
```
Error: S3 bucket {{bucket_name}} does not exist
```
**Cause**: Bucket doesn't exist or wrong name.
**Resolution**:
```bash
# Verify bucket exists
aws s3 ls s3://{{bucket_name}}/ --region {{region}}

# Create bucket if needed
aws s3api create-bucket \
  --bucket {{bucket_name}} \
  --region {{region}}
  
# If us-east-1 (no LocationConstraint needed)
aws s3api create-bucket \
  --bucket {{bucket_name}}
```

#### InsufficientS3BucketPolicy
```
Error: S3 bucket policy insufficient for CloudTrail
```
**Cause**: Bucket policy doesn't allow CloudTrail write access.
**Resolution**:
```bash
# Get current account ID
account_id=$(aws sts get-caller-identity --query Account --output text)

# Apply correct bucket policy
aws s3api put-bucket-policy \
  --bucket {{bucket_name}} \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"AWSCloudTrailAclCheck\",
        \"Effect\": \"Allow\",
        \"Principal\": {\"Service\": \"cloudtrail.amazonaws.com\"},
        \"Action\": \"s3:GetBucketAcl\",
        \"Resource\": \"arn:aws:s3:::{{bucket_name}}\"
      },
      {
        \"Sid\": \"AWSCloudTrailWrite\",
        \"Effect\": \"Allow\",
        \"Principal\": {\"Service\": \"cloudtrail.amazonaws.com\"},
        \"Action\": \"s3:PutObject\",
        \"Resource\": \"arn:aws:s3:::{{bucket_name}}/{{prefix}}/AWSLogs/${account_id}/*\",
        \"Condition\": {\"StringEquals\": {\"s3:x-amz-acl\": \"bucket-owner-full-control\"}}
      }
    ]
  }"
```

#### S3BucketNotPublic
```
Error: S3 bucket policy allows public access
```
**Cause**: Bucket has overly permissive public access settings.
**Resolution**:
```bash
# Check bucket public access settings
aws s3api get-public-access-block --bucket {{bucket_name}}

# Disable public access block (if needed for CloudTrail)
aws s3api put-public-access-block \
  --bucket {{bucket_name}} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

### CloudWatch Logs Errors

#### InvalidCloudWatchLogsLogGroup
```
Error: CloudWatch Logs log group does not exist
```
**Cause**: Log group not created before trail configuration.
**Resolution**:
```bash
# Create log group
aws logs create-log-group --log-group-name {{log_group_name}}

# Get log group ARN
log_group_arn=$(aws logs describe-log-groups \
  --log-group-name-prefix {{log_group_name}} \
  --query "logGroups[0].arn" \
  --output text)

# Update trail
aws cloudtrail update-trail \
  --name {{trail_name}} \
  --cloud-watch-logs-log-group-arn ${log_group_arn} \
  --cloud-watch-logs-role-arn {{role_arn}}
```

#### InvalidCloudWatchLogsRole
```
Error: CloudWatch Logs role does not have sufficient permissions
```
**Cause**: IAM role lacks CloudTrail to CloudWatch Logs permissions.
**Resolution**:
```bash
# Create correct trust policy
aws iam create-role \
  --role-name CloudTrail_CloudWatchLogs_Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach CloudWatch Logs policy
aws iam put-role-policy \
  --role-name CloudTrail_CloudWatchLogs_Role \
  --policy-name CloudTrailPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:*:*:log-group:{{log_group_name}}:log-stream:*"
    }]
  }'
```

### KMS Errors

#### KMSKeyNotFound
```
Error: KMS key does not exist
```
**Cause**: KMS key ARN/ID incorrect or in different region.
**Resolution**:
```bash
# List available keys
aws kms list-keys --region {{region}}

# Verify key exists
aws kms describe-key --key-id {{key_id}} --region {{region}}

# Check key is enabled
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.Enabled" \
  --output text
```

#### KMSAccessDenied
```
Error: Access denied to KMS key
```
**Cause**: IAM permissions insufficient for KMS operations.
**Resolution**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}"
    }
  ]
}
```

### Organization Trail Errors

#### OrganizationNotFound
```
Error: AWS Organization does not exist
```
**Cause**: Attempting to create organization trail without AWS Organizations.
**Resolution**:
```bash
# Check organization status
aws organizations describe-organization

# If no organization exists, create one
# Note: This requires additional steps and root account
aws organizations create-organization
```

#### NotOrganizationMasterAccount
```
Error: Not organization management account
```
**Cause**: Attempting to create organization trail from non-management account.
**Resolution**:
```bash
# Get organization info
aws organizations describe-organization

# Check if current account is management
master_id=$(aws organizations describe-organization \
  --query "Organization.MasterAccountId" \
  --output text)
  
current_id=$(aws sts get-caller-identity --query Account --output text)

if [ "$master_id" != "$current_id" ]; then
  echo "Must use management account: $master_id"
fi
```

#### InsufficientEncryptionPolicy
```
Error: Organization trail requires encryption key with organization access
```
**Cause**: KMS key policy doesn't allow cross-account access for organization.
**Resolution**:
```json
{
  "Sid": "Allow Organization Access",
  "Effect": "Allow",
  "Principal": {
    "AWS": "*"
  },
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey*"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:CallerAccount": "{{member_account_id}}",
      "kms:ViaService": "s3.{{region}}.amazonaws.com"
    }
  }
}
```

### Event Selector Errors

#### InvalidEventSelectors
```
Error: Invalid event selector configuration
```
**Cause**: Event selectors format incorrect or exceed limits.
**Resolution**:
- Max 5 event selectors per trail
- Valid resource types: `AWS::S3::Object`, `AWS::Lambda::Function`
- ARN format must be correct
- For S3: `arn:aws:s3:::bucket/*` (not just bucket ARN)

### Lookup Events Errors

#### InvalidTimeRange
```
Error: Invalid time range for lookup-events
```
**Cause**: Time range exceeds 90 days or is invalid.
**Resolution**:
```bash
# Lookup-events only supports last 90 days
# For older events, query S3 logs directly

# Check valid time range
start="2024-01-01T00:00:00Z"
end="2024-01-31T23:59:59Z"

# Max 90 days from now
max_age=$(date -d "90 days ago" -u +%Y-%m-%dT%H:%M:%SZ)
```

#### InvalidLookupAttribute
```
Error: Invalid lookup attribute key or value
```
**Cause**: Lookup attribute key not supported or value format wrong.
**Resolution**:
Supported AttributeKeys:
- EventId
- EventName
- EventSource
- Username
- ResourceType
- ResourceName

## Throttling Handling

### API Rate Limits
```
Error: ThrottlingException: Rate exceeded
```
**Cause**: Too many CloudTrail API calls.

**Resolution**:
```python
import time
import random

def exponential_backoff_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                delay = min(2 ** attempt * 0.5 + random.uniform(0, 0.5), 60)
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## Delivery Issues

### Logs Not Delivering

#### Symptoms
- Trail shows IsLogging: true
- No new log files in S3
- LastDeliveryTime not updating

#### Diagnosis
```bash
# Check trail status
aws cloudtrail get-trail-status --name {{trail_name}}

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket {{bucket_name}}

# Check CloudTrail service access
aws cloudtrail describe-trails --trail-name-list {{trail_name}} \
  --query "trailList[0].S3BucketName"

# Verify IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{{account_id}}:role/{{role_name}} \
  --action-names s3:PutObject \
  --resource-arns arn:aws:s3:::{{bucket_name}}/AWSLogs/{{account_id}}/*
```

#### Resolution Steps
1. Verify S3 bucket policy allows CloudTrail
2. Check bucket is in same region as trail
3. Verify no S3 bucket policy denies CloudTrail
4. Check IAM role permissions if using CloudWatch
5. Review CloudTrail service health (AWS Status Page)

### Log File Validation Failing

#### Symptoms
- Digest files not created
- Validation errors
- Digest delivery delayed

#### Resolution
```bash
# Manually validate logs
aws cloudtrail validate-logs \
  --trail-arn {{trail_arn}} \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --s3-bucket {{bucket_name}} \
  --s3-prefix {{prefix}}
```

## Data Events Issues

### S3 Data Events Not Logging

#### Symptoms
- Management events logging
- Data events configured but not appearing
- No PutObject events

#### Diagnosis
```bash
# Check event selectors
aws cloudtrail get-event-selectors --trail-name {{trail_name}}

# Verify data events enabled
event_selectors=$(aws cloudtrail get-event-selectors \
  --trail-name {{trail_name}} \
  --query "EventSelectors[].IncludeManagementEvents" \
  --output text)

# Check S3 bucket ARN format
data_resources=$(aws cloudtrail get-event-selectors \
  --trail-name {{trail_name}} \
  --query "EventSelectors[].DataResources[].Values" \
  --output text)
```

#### Resolution
```bash
# Correct S3 data events configuration
aws cloudtrail put-event-selectors \
  --trail-name {{trail_name}} \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::{{bucket_name}}/*"]
    }]
  }]'
```

**Note**: Use `/*` suffix for object-level, not just bucket ARN.

### Lambda Data Events Missing

#### Resolution
```bash
aws cloudtrail put-event-selectors \
  --trail-name {{trail_name}} \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::Lambda::Function",
      "Values": ["arn:aws:lambda:{{region}}:{{account_id}}:function:{{function_name}}"]
    }]
  }]'
```

## Organization Trail Issues

### Member Account Events Not Logging

#### Symptoms
- Organization trail created
- Only management account events visible
- Missing member account events

#### Diagnosis
```bash
# Check organization trail status in member accounts
aws cloudtrail describe-trails \
  --query "trailList[?IsOrganizationTrail==\`true\`]"

# Verify SCPs allow CloudTrail
aws organizations describe-effective-policy \
  --policy-type SERVICE_CONTROL_POLICY \
  --target-id {{account_id}}
```

#### Resolution
1. Ensure member accounts haven't opted out
2. Check Organization SCPs don't deny CloudTrail
3. Verify member accounts are active in organization
4. Confirm trail is visible in member account describe-trails

### Cross-Account Encryption

#### Symptoms
- Organization trail with KMS
- Member account logs unreadable
- KMS decryption errors

#### Resolution
Update KMS key policy to allow organization:
```json
{
  "Sid": "Allow Organization Decrypt",
  "Effect": "Allow",
  "Principal": {
    "AWS": "*"
  },
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:CallerAccount": "*",
      "kms:ViaService": "s3.*.amazonaws.com"
    },
    "StringLike": {
      "aws:PrincipalOrgID": "o-*"
    }
  }
}
```

## Recovery Procedures

### Trail Recovery Flow
```
1. Check trail status with get-trail-status
2. If IsLogging: false, check trail configuration
3. For S3 issues:
   - Verify bucket exists and is accessible
   - Check bucket policy
   - Verify IAM permissions
4. For CloudWatch Logs issues:
   - Check log group exists
   - Verify IAM role permissions
5. Restart logging if stopped
6. Max 3 retries for transient errors
```

### Event History Recovery
```
1. For events < 90 days: use lookup-events API
2. For events > 90 days: query S3 log files
3. Use Athena for SQL queries on S3 logs
4. Parse JSON log files programmatically
5. Cross-reference with CloudWatch Logs if enabled
```

### Audit Investigation Flow
```
1. Use lookup-events for recent activity (90 days)
2. Filter by username, event name, time range
3. Download S3 log files for detailed analysis
4. Use CloudWatch Logs Insights for queries
5. Correlate with VPC Flow Logs if needed
```

## Monitoring Checklist

| Metric/Check | Warning | Critical | Action |
|--------------|---------|----------|--------|
| IsLogging | false | N/A | Restart logging |
| LatestDeliveryTime | > 1 hour | > 6 hours | Check S3/config |
| LatestDeliveryError | any | persistent | Fix configuration |
| ThrottledRequests | > 10 | > 100 | Implement backoff |
| Log file count | 0/day | 0 for 24h | Check trail status |