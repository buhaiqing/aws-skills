# AWS CLI Usage - CloudTrail

AWS CLI commands for CloudTrail operations. All commands use `--region {{r.region}} --output json`.

## Common JSON Paths (Centralized)

```
# Create Trail:      .Trail.{TrailARN,Name,S3BucketName}
# Describe Trails:   .trailList[].{Name,TrailARN,S3BucketName,IsMultiRegionTrail,HomeRegion}
# Get Trail Status:  .{IsLogging,LatestDeliveryTime,LatestDeliveryError}
# Lookup Events:     .Events[].{EventId,EventTime,EventSource,EventName,Username,SourceIPAddress}
# Get Event Sel:     .EventSelectors[].{ReadWriteType,IncludeManagementEvents}
# Put Event Sel:     .EventSelectors[]
# Get Insight Sel:   .InsightSelectors[].InsightType
# Start/Stop:        Empty (success)
```

## Trail Operations

### Create Trail
```bash
aws cloudtrail create-trail \
  --name {{user.TrailName}} --s3-bucket-name {{user.S3BucketName}} \
  --is-multi-region-trail --enable-log-file-validation \
  --kms-key-id {{user.KmsKeyId}} --is-organization-trail \
  --tags-list Key=Environment,Value=production
```

### Describe Trails
```bash
aws cloudtrail describe-trails --trail-name-list {{user.TrailName}}
aws cloudtrail describe-trails    # All trails
```

### Get Trail Status
```bash
aws cloudtrail get-trail-status --name {{user.TrailName}}
```

### Update Trail
```bash
aws cloudtrail update-trail --name {{user.TrailName}} \
  --s3-bucket-name {{user.NewS3BucketName}} --kms-key-id {{user.NewKmsKeyId}}
```

### Delete / Start / Stop Logging
```bash
aws cloudtrail delete-trail --name {{user.TrailName}}
aws cloudtrail start-logging --name {{user.TrailName}}
aws cloudtrail stop-logging --name {{user.TrailName}}
```

## Event Operations

### Lookup Events
```bash
# Basic — last 90 days
aws cloudtrail lookup-events

# By time range
aws cloudtrail lookup-events --start-time "2024-01-01T00:00:00Z" --end-time "2024-01-15T23:59:59Z"

# By user/event/resource
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue={{user.UserName}}
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=CreateTrail
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=ec2.amazonaws.com

# Pagination
aws cloudtrail lookup-events --max-results 50 --next-token {{user.NextToken}}
```

### Common Lookup Attributes
| AttributeKey | Description | Example |
|-------------|-------------|---------|
| EventId | Specific event ID | 12345678-... |
| EventName | API action | CreateTrail |
| EventSource | Service | ec2.amazonaws.com |
| Username | IAM user/role | admin |
| ResourceType | Resource type | AWS::EC2::Instance |
| ResourceName | Resource name | i-1234567890 |

## Event Selectors

### Get / Put Event Selectors
```bash
aws cloudtrail get-event-selectors --trail-name {{user.TrailName}}

# Management events only
aws cloudtrail put-event-selectors --trail-name {{user.TrailName}} \
  --event-selectors '{"ReadWriteType":"All","IncludeManagementEvents":true}'

# With S3 data events
aws cloudtrail put-event-selectors --trail-name {{user.TrailName}} \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::{{user.BucketName}}/*"]}]}]'
```

## Insights Configuration

```bash
aws cloudtrail get-insight-selectors --trail-name {{user.TrailName}}
aws cloudtrail put-insight-selectors --trail-name {{user.TrailName}} \
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'
```

## S3 Bucket Policy for CloudTrail
```bash
aws s3api put-bucket-policy --bucket {{user.S3BucketName}} --policy '{
  "Version":"2012-10-17","Statement":[
    {"Sid":"AWSCloudTrailAclCheck","Effect":"Allow","Principal":{"Service":"cloudtrail.amazonaws.com"},"Action":"s3:GetBucketAcl","Resource":"arn:aws:s3:::{{user.S3BucketName}}"},
    {"Sid":"AWSCloudTrailWrite","Effect":"Allow","Principal":{"Service":"cloudtrail.amazonaws.com"},"Action":"s3:PutObject","Resource":"arn:aws:s3:::{{user.S3BucketName}}/{{user.S3KeyPrefix}}/AWSLogs/{{user.AccountId}}/*","Condition":{"StringEquals":{"s3:x-amz-acl":"bucket-owner-full-control"}}}
  ]}'
```

## Common Event Queries

```bash
# Recent console logins
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin --max-results 10

# Failed API calls
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue={{user.EventName}} | jq '.Events[] | select(.ErrorCode != null)'

# Events by specific user
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue={{user.UserName}} --start-time "2024-01-01T00:00:00Z" --end-time "2024-01-31T23:59:59Z"
```