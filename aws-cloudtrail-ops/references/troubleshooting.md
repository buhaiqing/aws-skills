# CloudTrail Troubleshooting

## Error Code Reference

### Trail Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **TrailAlreadyExists** | Trail name exists in region | Use different name or `update-trail` | [→](troubleshooting-details/trail-errors.md) |
| **TrailNotFound** | Deleted/wrong name/wrong region | `describe-trails`, check home region | [→](troubleshooting-details/trail-errors.md) |
| **TrailNotProvided** | Missing required parameter | Specify `--name` or `--trail-name-list` | - |
| **InvalidTrailName** | Name doesn't meet requirements | 3-128 chars, alphanumeric/underscore/hyphen/period | - |

### S3 Bucket Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **S3BucketNotFound** | Bucket doesn't exist or wrong name | `aws s3 ls` or create bucket | [→](troubleshooting-details/s3-errors.md) |
| **InsufficientS3BucketPolicy** | Policy doesn't allow CloudTrail write | Add CloudTrail policy | [→](troubleshooting-details/s3-errors.md) |
| **S3BucketNotPublic** | Overly permissive public access | Adjust public access block | [→](troubleshooting-details/s3-errors.md) |

### CloudWatch Logs Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **InvalidCloudWatchLogsLogGroup** | Log group not created | `create-log-group` → `update-trail` | [→](troubleshooting-details/cw-logs-errors.md) |
| **InvalidCloudWatchLogsRole** | IAM role lacks permissions | Create role with CloudTrail trust | [→](troubleshooting-details/cw-logs-errors.md) |

### KMS Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **KMSKeyNotFound** | Wrong key ARN/ID or region | `list-keys` + `describe-key` | [→](troubleshooting-details/kms-errors.md) |
| **KMSAccessDenied** | Insufficient KMS permissions | Add `kms:GenerateDataKey*` + `kms:DescribeKey` | [→](troubleshooting-details/kms-errors.md) |

### Organization Trail Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **OrganizationNotFound** | No AWS Organizations | `describe-organization` or create | [→](troubleshooting-details/org-trail-errors.md) |
| **NotOrganizationMasterAccount** | Non-management account | Use management account | [→](troubleshooting-details/org-trail-errors.md) |
| **InsufficientEncryptionPolicy** | KMS policy lacks org access | Add org conditions to KMS policy | [→](troubleshooting-details/org-trail-errors.md) |

### Event Selector Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **InvalidEventSelectors** | Format incorrect/exceeds limits | Max 5 selectors; use `bucket/*` for S3 | [→](troubleshooting-details/event-selectors.md) |
| **InvalidTimeRange** | Exceeds 90 days | Use S3 logs for older events | [→](troubleshooting-details/event-selectors.md) |
| **InvalidLookupAttribute** | Unsupported key | Valid: EventId, EventName, EventSource, Username, ResourceType, ResourceName | [→](troubleshooting-details/event-selectors.md) |

## Throttling

| Trigger | Resolution |
|---------|------------|
| **ThrottlingException** | Exponential backoff: `delay = min(2^attempt * 0.5 + random(0, 0.5), 60)`, max 5 retries |

## Delivery Issues

| Symptom | Diagnosis | Resolution | Details |
|---------|-----------|------------|---------|
| `IsLogging: true` but no S3 logs | `get-trail-status` → `LatestDeliveryTime` | Verify S3 policy, IAM, region | [→](troubleshooting-details/delivery-issues.md) |
| Digest files not created | `validate-logs` | Enable validation, check S3 policy | [→](troubleshooting-details/delivery-issues.md) |
| LastDeliveryTime stale >6h | `describe-trails` | Restart logging or fix access | [→](troubleshooting-details/delivery-issues.md) |

## Data Events Issues

| Symptom | Diagnosis | Resolution | Details |
|---------|-----------|------------|---------|
| S3 data events not logging | `get-event-selectors` → `DataResources` | Use `arn:aws:s3:::bucket/*` | [→](troubleshooting-details/data-events.md) |
| Lambda data events missing | `get-event-selectors` → Lambda ARN | Use full function ARN | [→](troubleshooting-details/data-events.md) |

## Organization Trail Issues

| Symptom | Diagnosis | Resolution | Details |
|---------|-----------|------------|---------|
| Only mgmt account events | `describe-trails` → `IsOrganizationTrail` | Verify members active, SCPs allow | [→](troubleshooting-details/org-trail-issues.md) |
| Member logs unreadable | KMS decryption errors | Update KMS with `aws:PrincipalOrgID` | [→](troubleshooting-details/org-trail-issues.md) |

## Recovery Flow

```
1. get-trail-status → check IsLogging
2. If false → check trail config + S3 bucket
3. For S3 issues → verify bucket exists + policy + IAM
4. For CW Logs issues → verify log group + role
5. Restart logging if stopped
6. Max 3 retries for transient errors
```

## Event History

| Time Range | Query Method |
|------------|--------------|
| <90 days | `lookup-events` API |
| >90 days | Query S3 log files directly (use Athena for SQL) |

## Monitoring Checklist

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| IsLogging | false | N/A | Restart logging |
| LatestDeliveryTime | >1 hour | >6 hours | Check S3/config |
| LatestDeliveryError | any | persistent | Fix configuration |
| ThrottledRequests | >10 | >100 | Implement backoff |
| Log file count | 0/day | 0 for 24h | Check trail status |
