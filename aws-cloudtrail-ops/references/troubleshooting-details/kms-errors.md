# CloudTrail KMS Errors — Detailed Recovery

## KMSKeyNotFound

KMS key ARN/ID incorrect or in different region.

```bash
aws kms list-keys --region {{region}}
aws kms describe-key --key-id {{key_id}} --region {{region}}
aws kms describe-key --key-id {{key_id}} --query "KeyMetadata.Enabled" --output text
```

## KMSAccessDenied

IAM permissions insufficient for KMS operations.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["kms:GenerateDataKey*", "kms:DescribeKey"],
    "Resource": "arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}"
  }]
}
```
