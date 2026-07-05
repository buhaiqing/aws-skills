# KMS Grant Errors — Detailed Recovery

## InvalidGrantIdException

Grant ID incorrect or already retired.

```bash
# List grants for key
aws kms list-grants --key-id {{key_id}}

# Verify specific grant
aws kms list-grants --key-id {{key_id}} --query "Grants[?GrantId=='{{grant_id}}']"
```

## InvalidGrantTokenException

Grant token expired, revoked, or key deleted.

```bash
# Create new grant
aws kms create-grant \
  --key-id {{key_id}} \
  --grantee-principal {{grantee}} \
  --operations Encrypt Decrypt \
  --name {{grant_name}}
```
