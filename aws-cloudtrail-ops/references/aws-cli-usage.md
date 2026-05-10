# AWS CLI Usage - CloudTrail

AWS CLI commands for CloudTrail operations. All commands use `--output json`.

## Trail Operations

### Create Trail
```bash
aws cloudtrail create-trail \
  --name {{user.TrailName}} \
  --s3-bucket-name {{user.S3BucketName}} \
  --s3-key-prefix {{user.S3KeyPrefix}} \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --kms-key-id {{user.KmsKeyId}} \
  --is-organization-trail \
  --tags-list Key=Environment,Value=production Key=Team,Value=platform \
  --output json
```

**JSON paths:**
- `.Trail.Name` → trail name
- `.Trail.S3BucketName` → S3 bucket
- `.Trail.S3KeyPrefix` → prefix
- `.Trail.TrailARN` → ARN
- `.Trail.IsMultiRegionTrail` → boolean
- `.Trail.LogFileValidationEnabled` → boolean
- `.Trail.KmsKeyId` → KMS key

### Describe Trails
```bash
# Single trail
aws cloudtrail describe-trails \
  --trail-name-list {{user.TrailName}} \
  --output json

# All trails
aws cloudtrail describe-trails --output json
```

**JSON paths:**
- `.trailList[].Name` → trail name
- `.trailList[].S3BucketName` → S3 bucket
- `.trailList[].S3KeyPrefix` → prefix
- `.trailList[].TrailARN` → ARN
- `.trailList[].HomeRegion` → home region
- `.trailList[].IsMultiRegionTrail` → boolean
- `.trailList[].IsOrganizationTrail` → boolean
- `.trailList[].LogFileValidationEnabled` → boolean
- `.trailList[].KmsKeyId` → encryption key

### Get Trail Status
```bash
aws cloudtrail get-trail-status \
  --name {{user.TrailName}} \
  --output json
```

**JSON paths:**
- `.IsLogging` → boolean, if trail is actively logging
- `.LatestDeliveryTime` → last successful delivery
- `.LatestDeliveryError` → error message if failed
- `.LatestNotificationTime` → SNS notification time
- `.LatestNotificationError` → SNS error message
- `.StartLoggingTime` → when logging started
- `.StopLoggingTime` → when logging stopped

### Update Trail
```bash
aws cloudtrail update-trail \
  --name {{user.TrailName}} \
  --s3-bucket-name {{user.NewS3BucketName}} \
  --s3-key-prefix {{user.NewS3KeyPrefix}} \
  --kms-key-id {{user.NewKmsKeyId}} \
  --output json
```

### Delete Trail
```bash
aws cloudtrail delete-trail \
  --name {{user.TrailName}} \
  --output json
```

**Safety Gate:** Human confirmation required before deletion.

### Start Logging
```bash
aws cloudtrail start-logging \
  --name {{user.TrailName}} \
  --output json
```

### Stop Logging
```bash
aws cloudtrail stop-logging \
  --name {{user.TrailName}} \
  --output json
```

## Event Operations

### Lookup Events
```bash
# Basic lookup - last 7 days
aws cloudtrail lookup-events \
  --output json

# Lookup by time range
aws cloudtrail lookup-events \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-15T23:59:59Z" \
  --output json

# Lookup by username
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue={{user.UserName}} \
  --output json

# Lookup by event name
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateTrail \
  --output json

# Lookup by event source
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=ec2.amazonaws.com \
  --output json

# Lookup by resource type and name
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::S3::Bucket \
  --output json

# Pagination
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --max-results 50 \
  --next-token {{user.NextToken}} \
  --output json
```

**JSON paths:**
- `.Events[].EventId` → unique event ID
- `.Events[].EventTime` → ISO 8601 timestamp
- `.Events[].EventSource` → service (e.g., ec2.amazonaws.com)
- `.Events[].EventName` → API action (e.g., RunInstances)
- `.Events[].EventType` → AwsApiCall, AwsServiceEvent, etc.
- `.Events[].Username` → IAM user/role name
- `.Events[].UserAgent` → user agent string
- `.Events[].SourceIPAddress` → source IP
- `.Events[].RequestParameters` → request details
- `.Events[].ResponseElements` → response details
- `.Events[].CloudTrailEvent` → full JSON event
- `.NextToken` → for pagination

### Common Lookup Attributes

| AttributeKey | Description | Example |
|--------------|-------------|---------|
| EventId | Specific event ID | 12345678-... |
| EventName | API action name | CreateTrail |
| EventSource | Service name | ec2.amazonaws.com |
| Username | IAM user/role | admin |
| ResourceType | Resource type | AWS::EC2::Instance |
| ResourceName | Resource name | i-1234567890abcdef0 |

## Event Selector Operations

### Get Event Selectors
```bash
aws cloudtrail get-event-selectors \
  --trail-name {{user.TrailName}} \
  --output json
```

**JSON paths:**
- `.EventSelectors[].ReadWriteType` → All, ReadOnly, WriteOnly
- `.EventSelectors[].IncludeManagementEvents` → boolean
- `.EventSelectors[].DataResources[].Type` → resource type
- `.EventSelectors[].DataResources[].Values[]` → resource ARNs

### Put Event Selectors
```bash
# Basic - management events only
aws cloudtrail put-event-selectors \
  --trail-name {{user.TrailName}} \
  --event-selectors '{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true
  }' \
  --output json

# With S3 data events
aws cloudtrail put-event-selectors \
  --trail-name {{user.TrailName}} \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::{{user.BucketName}}/*"]
    }]
  }]' \
  --output json

# With Lambda data events
aws cloudtrail put-event-selectors \
  --trail-name {{user.TrailName}} \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::Lambda::Function",
      "Values": ["arn:aws:lambda:us-east-1:{{user.AccountId}}:function:{{user.FunctionName}}"]
    }]
  }]' \
  --output json

# Multiple data resources
aws cloudtrail put-event-selectors \
  --trail-name {{user.TrailName}} \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [
      {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::bucket1/*", "arn:aws:s3:::bucket2/*"]},
      {"Type": "AWS::Lambda::Function", "Values": ["arn:aws:lambda:*:*:function:*"]}
    ]
  }]' \
  --output json
```

## CloudWatch Logs Integration

### Create CloudWatch Log Group
```bash
aws logs create-log-group --log-group-name {{user.LogGroupName}}
```

### Update Trail with CloudWatch Logs
```bash
aws cloudtrail update-trail \
  --name {{user.TrailName}} \
  --cloud-watch-logs-log-group-arn {{user.LogGroupArn}} \
  --cloud-watch-logs-role-arn {{user.CloudWatchRoleArn}} \
  --output json
```

## S3 Bucket Policy for CloudTrail

```bash
aws s3api put-bucket-policy \
  --bucket {{user.S3BucketName}} \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AWSCloudTrailAclCheck",
        "Effect": "Allow",
        "Principal": {
          "Service": "cloudtrail.amazonaws.com"
        },
        "Action": "s3:GetBucketAcl",
        "Resource": "arn:aws:s3:::{{user.S3BucketName}}"
      },
      {
        "Sid": "AWSCloudTrailWrite",
        "Effect": "Allow",
        "Principal": {
          "Service": "cloudtrail.amazonaws.com"
        },
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::{{user.S3BucketName}}/{{user.S3KeyPrefix}}/AWSLogs/{{user.AccountId}}/*",
        "Condition": {
          "StringEquals": {
            "s3:x-amz-acl": "bucket-owner-full-control"
          }
        }
      }
    ]
  }'
```

## Organization Trail

### Create Organization Trail
```bash
aws cloudtrail create-trail \
  --name {{user.TrailName}} \
  --s3-bucket-name {{user.S3BucketName}} \
  --is-organization-trail \
  --output json
```

**Requirements:**
- Must be created from organization management account
- S3 bucket must allow access from all member accounts
- Organization ID must be allowed in bucket policy

## Insights Configuration

### Get Insights Selectors
```bash
aws cloudtrail get-insight-selectors \
  --trail-name {{user.TrailName}} \
  --output json
```

### Put Insights Selectors
```bash
aws cloudtrail put-insight-selectors \
  --trail-name {{user.TrailName}} \
  --insight-selectors '[{
    "InsightType": "ApiCallRateInsight"
  }, {
    "InsightType": "ApiErrorRateInsight"
  }]' \
  --output json
```

## Common Options

```bash
--name {{user.TrailName}}                    # Trail name
--s3-bucket-name {{user.S3BucketName}}         # S3 bucket
--s3-key-prefix {{user.S3KeyPrefix}}           # Prefix for logs
--is-multi-region-trail                        # Enable multi-region
--is-organization-trail                        # Enable for organization
--enable-log-file-validation                   # Enable log integrity
--kms-key-id {{user.KmsKeyId}}                 # KMS encryption
--cloud-watch-logs-log-group-arn {{user.LogGroupArn}}  # CloudWatch Logs
--cloud-watch-logs-role-arn {{user.RoleArn}}   # CloudWatch Logs role
--tags-list Key=Name,Value=production          # Tags
--include-global-service-events                # Include global services
--event-selectors                              # Data event selectors
```

## Querying CloudTrail Logs in S3

### List Log Files
```bash
aws s3 ls s3://{{user.S3BucketName}}/{{user.S3KeyPrefix}}/AWSLogs/{{user.AccountId}}/CloudTrail/{{user.Region}}/2024/01/01/ \
  --recursive
```

### Download and Analyze
```bash
# Download specific log file
aws s3 cp s3://{{user.S3BucketName}}/{{user.S3KeyPrefix}}/AWSLogs/{{user.AccountId}}/CloudTrail/{{user.Region}}/2024/01/01/logfile.json.gz .

# Extract and query
gunzip logfile.json.gz
jq '.Records[] | select(.eventName=="CreateTrail")' logfile.json
```

## Common Event Queries

### Recent Console Login
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --max-results 10 \
  --output json
```

### Failed API Calls
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue={{user.EventName}} \
  --output json | \
  jq '.Events[] | select(.ErrorCode != null)'
```

### Events by Specific User
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue={{user.UserName}} \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-31T23:59:59Z" \
  --output json
```

### S3 PutObject Events
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --max-results 100 \
  --output json
```