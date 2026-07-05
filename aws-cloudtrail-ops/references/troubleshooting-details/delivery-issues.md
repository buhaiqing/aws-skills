# CloudTrail Delivery Issues — Detailed Recovery

## Logs Not Delivering

Trail shows `IsLogging: true` but no new log files in S3.

```bash
# Check trail status
aws cloudtrail get-trail-status --name {{trail_name}}

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket {{bucket_name}}

# Verify IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{{account_id}}:role/{{role_name}} \
  --action-names s3:PutObject \
  --resource-arns arn:aws:s3:::{{bucket_name}}/AWSLogs/{{account_id}}/*
```

**Resolution steps:**
1. Verify S3 bucket policy allows CloudTrail
2. Check bucket is in same region as trail
3. Verify no S3 bucket policy denies CloudTrail
4. Check IAM role permissions if using CloudWatch
5. Review CloudTrail service health (AWS Status Page)

## Log File Validation Failing

Digest files not created or validation errors.

```bash
aws cloudtrail validate-logs \
  --trail-arn {{trail_arn}} \
  --start-time 2024-01-01T00:00:00Z --end-time 2024-01-31T23:59:59Z \
  --s3-bucket {{bucket_name}} --s3-prefix {{prefix}}
```
