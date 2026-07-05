# CloudTrail Organization Trail Issues — Detailed Recovery

## Member Account Events Not Logging

Organization trail created but only management account events visible.

```bash
# Check organization trail status
aws cloudtrail describe-trails --query "trailList[?IsOrganizationTrail==\`true\`]"

# Verify SCPs allow CloudTrail
aws organizations describe-effective-policy \
  --policy-type SERVICE_CONTROL_POLICY --target-id {{account_id}}
```

**Resolution:**
1. Ensure member accounts haven't opted out
2. Check Organization SCPs don't deny CloudTrail
3. Verify member accounts are active in organization
4. Confirm trail is visible in member account `describe-trails`

## Cross-Account Encryption

Organization trail with KMS; member account logs unreadable.

Update KMS key policy:
```json
{
  "Sid": "Allow Organization Decrypt",
  "Effect": "Allow",
  "Principal": {"AWS": "*"},
  "Action": "kms:Decrypt",
  "Resource": "*",
  "Condition": {
    "StringEquals": {"kms:CallerAccount": "*", "kms:ViaService": "s3.*.amazonaws.com"},
    "StringLike": {"aws:PrincipalOrgID": "o-*"}
  }
}
```
