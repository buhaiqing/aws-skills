# CloudTrail Event Selectors — Detailed Recovery

## InvalidEventSelectors

Format incorrect or exceeds limits.

- Max 5 event selectors per trail
- Valid resource types: `AWS::S3::Object`, `AWS::Lambda::Function`
- ARN format: `arn:aws:s3:::bucket/*` (not just bucket ARN for S3 objects)

```bash
# Check current selectors
aws cloudtrail get-event-selectors --trail-name {{trail_name}}
```

## InvalidTimeRange

Time range exceeds 90 days.

- `lookup-events` only supports last 90 days
- For older events, query S3 logs directly (use Athena)

## InvalidLookupAttribute

Unsupported attribute key.

**Valid AttributeKeys:** EventId, EventName, EventSource, Username, ResourceType, ResourceName

```bash
# Example: lookup by event name
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Decrypt \
  --start-time 2024-01-01T00:00:00Z --end-time 2024-01-31T23:59:59Z
```
