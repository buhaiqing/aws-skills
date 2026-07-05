# KMS Key Not Found — Detailed Recovery

## NotFoundException

Key ID incorrect, deleted, or wrong region.

```bash
# List keys to verify existence
aws kms list-keys --output json

# Check if alias exists
aws kms list-aliases --query "Aliases[?AliasName=='alias/{{key_name}}']"

# Try with full ARN format
aws kms describe-key \
  --key-id arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}

# Check correct region
aws kms describe-key --key-id {{key_id}} --region {{correct_region}}
```
