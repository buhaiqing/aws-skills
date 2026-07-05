# KMS Cross-Account Access — Detailed Recovery

## Grant Creation Failed

Key policy must allow cross-account access.

```json
{
  "Sid": "Allow Cross-Account Grants",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::{{other_account_id}}:root"},
  "Action": ["kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant", "kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*", "kms:DescribeKey"],
  "Resource": "*"
}
```

## External Account Cannot Use Key

Both policies required:

**1. Key policy (owning account):**
```json
{
  "Sid": "Allow External Account",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::{{external_account_id}}:root"},
  "Action": "kms:*",
  "Resource": "*"
}
```

**2. IAM policy (external account):**
```json
{
  "Effect": "Allow",
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "arn:aws:kms:{{region}}:{{owning_account_id}}:key/{{key_id}}"
}
```
