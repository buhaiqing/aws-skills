# Troubleshooting — S3

## Common Error Codes & Recovery

| Error | HTTP | Agent Action | Max Retries |
|-------|------|-------------|-------------|
| BucketAlreadyExists | 409 | Use different name | 0 — HALT |
| InvalidBucketName | 400 | Fix naming (3-63 chars, lowercase, no special chars) | 1 — fix and retry |
| NoSuchBucket | 404 | Verify bucket name and region | 0 — HALT |
| NoSuchKey | 404 | Verify object key | 0 — HALT |
| AccessDenied | 403 | Add S3 permissions to IAM role | 0 — HALT |
| EntityTooLarge | 400 | Use multipart upload for large files | 1 — fix and retry |
| KeyTooLong | 400 | Shorten object key | 1 — fix and retry |
| InvalidRequest | 400 | Review API docs | 1 — fix and retry |
| ThrottlingException | 429 | Exponential backoff | 3 — HALT |
| InternalError | 500 | Backoff and retry | 3 — HALT |

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

## Performance Issues

| Symptom | Resolution |
|---------|------------|
| Slow list operations | Use prefix filtering; avoid listing entire bucket |
| High request costs | Use S3 Inventory; reduce LIST calls |
| Latency | Check region; use S3 Transfer Acceleration |