# KMS Permission Errors — Detailed Recovery

## AccessDeniedException

IAM permissions or key policy insufficient.

**IAM Policy Check:**
```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{{account_id}}:user/{{username}} \
  --action-names kms:Encrypt kms:Decrypt kms:DescribeKey \
  --resource-arns arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}
```

**Required IAM actions:** `kms:DescribeKey`, `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey`

**Key Policy Check:**
```bash
# Get key policy
aws kms get-key-policy --key-id {{key_id}} --policy-name default --query Policy --output text

# Example fix — add IAM user to key policy:
{
  "Sid": "Allow IAM User",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::{{account_id}}:user/{{username}}"},
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:DescribeKey"],
  "Resource": "*"
}
```

## PolicyLockoutSafetyCheck

Policy removes all admin access. Must keep root access or use bypass.

```bash
# Must keep at least root:
{
  "Sid": "Enable IAM User Permissions",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::{{account_id}}:root"},
  "Action": "kms:*",
  "Resource": "*"
}

# Or bypass (DANGEROUS):
aws kms put-key-policy --key-id {{key_id}} --policy-name default \
  --policy '{{user.Policy}}' --bypass-policy-lockout-safety-check
```

## MalformedPolicyDocumentException

Invalid JSON or policy structure.

```bash
# Validate JSON
python3 -c "import json; json.load(open('policy.json'))"

# Required elements: Version "2012-10-17", Statement array, Effect, Principal, Action, Resource
```
