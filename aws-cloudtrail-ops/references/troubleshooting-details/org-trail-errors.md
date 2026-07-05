# CloudTrail Organization Trail Errors — Detailed Recovery

## OrganizationNotFound

Attempting to create organization trail without AWS Organizations.

```bash
aws organizations describe-organization
# If no org exists, create one (requires root account)
aws organizations create-organization
```

## NotOrganizationMasterAccount

Non-management account attempting org trail.

```bash
master_id=$(aws organizations describe-organization --query "Organization.MasterAccountId" --output text)
current_id=$(aws sts get-caller-identity --query Account --output text)
[ "$master_id" != "$current_id" ] && echo "Must use management account: $master_id"
```

## InsufficientEncryptionPolicy

KMS key policy doesn't allow cross-account access for organization.

```json
{
  "Sid": "Allow Organization Access",
  "Effect": "Allow",
  "Principal": {"AWS": "*"},
  "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {"kms:CallerAccount": "{{member_account_id}}", "kms:ViaService": "s3.{{region}}.amazonaws.com"}
  }
}
```
