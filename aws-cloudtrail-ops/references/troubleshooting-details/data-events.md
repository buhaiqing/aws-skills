# CloudTrail Data Events — Detailed Recovery

## S3 Data Events Not Logging

Management events logging but data events not appearing.

```bash
# Check event selectors
aws cloudtrail get-event-selectors --trail-name {{trail_name}}

# Verify data events enabled
aws cloudtrail get-event-selectors --trail-name {{trail_name}} \
  --query "EventSelectors[].IncludeManagementEvents" --output text

# Check S3 bucket ARN format
aws cloudtrail get-event-selectors --trail-name {{trail_name}} \
  --query "EventSelectors[].DataResources[].Values" --output text
```

**Resolution:**
```bash
aws cloudtrail put-event-selectors --trail-name {{trail_name}} --event-selectors '[{
  "ReadWriteType": "All",
  "IncludeManagementEvents": true,
  "DataResources": [{"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::{{bucket_name}}/*"]}]
}]'
```

**Note:** Use `/*` suffix for object-level, not just bucket ARN.

## Lambda Data Events Missing

```bash
aws cloudtrail put-event-selectors --trail-name {{trail_name}} --event-selectors '[{
  "ReadWriteType": "All",
  "IncludeManagementEvents": true,
  "DataResources": [{"Type": "AWS::Lambda::Function", "Values": ["arn:aws:lambda:{{region}}:{{account_id}}:function:{{function_name}}"]}]
}]'
```
