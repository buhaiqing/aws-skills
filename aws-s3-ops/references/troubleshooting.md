# Troubleshooting — S3

## Common Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| BucketAlreadyExists | 409 | Bucket name taken globally | Use different name |
| InvalidBucketName | 400 | Name violates rules | Fix naming (3-63 chars, lowercase, no special chars) |
| NoSuchBucket | 404 | Bucket doesn't exist | Verify bucket name and region |
| NoSuchKey | 404 | Object doesn't exist | Verify object key |
| AccessDenied | 403 | IAM policy denies action | Add S3 permissions to IAM role |
| EntityTooLarge | 400 | Object > 5TB | Not possible; use multipart upload for large files |
| KeyTooLong | 400 | Key exceeds length limit | Shorten object key |
| InvalidRequest | 400 | Invalid parameter combination | Review API docs |
| ThrottlingException | 429 | Too many requests | Backoff; retry 3x |
| InternalError | 500 | AWS service issue | Retry 3x; HALT if persists |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify bucket exists**: `aws s3api head-bucket --bucket NAME`
3. **Verify region**: Check bucket region via `aws s3api get-bucket-location`
4. **Check permissions**: IAM policy for `s3:*` or specific actions
5. **List objects**: `aws s3api list-objects-v2 --bucket NAME`

## Common Issues

### Bucket Name Already Exists

| Symptom | Cause | Resolution |
|---------|-------|------------|
| BucketAlreadyExists | Global namespace collision | Use unique prefix (e.g., `company-project-env-bucket`) |
| Cannot create bucket | Name reserved by AWS | Avoid AWS prefix names |

### Access Denied

| Symptom | Cause | Resolution |
|---------|-------|------------|
| 403 on bucket operations | IAM policy missing `s3:*` | Add `s3:GetBucket*`, `s3:PutBucket*`, `s3:DeleteBucket*` |
| 403 on object operations | IAM policy missing object actions | Add `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` |
| 403 with public access | BlockPublicAccess enabled | Disable bucket-level BlockPublicAccess if public needed |

### Upload Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Slow upload | Large file without multipart | Use `aws s3 cp` (auto multipart) |
| Timeout | Network issue | Retry; use multipart upload |
| EntityTooLong | Key too long | Shorten key path |

### Download Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| NoSuchKey | Wrong key | Verify key (case-sensitive, full path) |
| 403 on get | IAM denies | Add `s3:GetObject` permission |

### Glacier Object Access

| Symptom | Cause | Resolution |
|---------|-------|------------|
| InvalidObjectState | Object archived | Restore first: `aws s3api restore-object` |
| AccessDenied on restore | Need restore permission | Add `s3:RestoreObject` |

## CloudWatch Logs Integration

Check S3 access logs:
```bash
aws logs filter-log-events \
  --log-group-name aws/s3/my-bucket/access-logs \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json
```

## Performance Issues

| Symptom | Resolution |
|---------|------------|
| Slow list operations | Use prefix filtering; avoid listing entire bucket |
| High request costs | Use S3 Inventory; reduce LIST calls |
| Latency | Check region; use S3 Transfer Acceleration |

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx Internal | 3 | Backoff; retry; HALT after 3 |
| 429 Throttling | 3 | Exponential backoff |
| 400 InvalidParameter | 1 | Fix; retry once |
| 409 BucketAlreadyExists | 0 | HALT; use different name |
| 404 NoSuchBucket/Key | 0 | HALT; verify name |