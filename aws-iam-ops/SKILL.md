---
name: aws-iam-ops
description: >-
  Use when managing AWS IAM users, groups, roles, and policies via AWS CLI or
  boto3 SDK; user mentions IAM, Identity and Access Management, user, group,
  role, policy, or permissions.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to IAM endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS IAM Operations Skill

## Overview

AWS IAM (Identity and Access Management) securely controls access to AWS resources. Manage authentication (who can sign in) and authorization (what permissions they have). This skill is an **operational runbook** for IAM identity and policy operations.

## Trigger & Scope

### SHOULD Use When
- User mentions "IAM", "Identity", "Access Management", "permissions"
- Task involves **users, groups, roles, policies** (create, list, attach, delete)
- Keywords: user, group, role, policy, permission, trust-policy, access-key

### SHOULD NOT Use When
- EC2 instance ops → delegate to: `aws-ec2-ops`
- S3 bucket ops → delegate to: `aws-s3-ops`
- Billing → delegate to: `aws-cost-ops`
- Security audit/compliance → specialized security skill (if exists)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | IAM is global; region for STS only |
| `{{user.user_name}}` | User input | Ask once; reuse |
| `{{user.role_name}}` | User input | Ask once; reuse |
| `{{output.arn}}` | Last API response | Parse: `.User.Arn` or `.Role.Arn` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**

```
Pre-flight → Execute (CLI/SDK) → Validate → Recover (On Error)
```

### Operation: Create User

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; configure credentials |
| User name valid | Check naming rules | Suggest valid name |
| Path valid (optional) | Verify path format | Use default `/` |

#### Execute — CLI (Primary)
```bash
aws iam create-user \
  --user-name "{{user.user_name}}" \
  --path "{{user.path}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('iam')
response = client.create_user(
    UserName='{{user.user_name}}',
    Path='{{user.path}}'
)
```

#### Validate
```bash
aws iam get-user --user-name "{{user.user_name}}" --output json
```

#### Recover
| Error | Action |
|-------|--------|
| EntityAlreadyExists | HALT; user already exists |
| InvalidInput | Fix name/path; retry once |
| Throttling (429) | Backoff, retry 3x |

### Operation: Create Role

#### Pre-flight
- Trust policy JSON must be provided
- Verify trust policy structure (Principal, Action, Condition)

#### Execute — CLI
```bash
aws iam create-role \
  --role-name "{{user.role_name}}" \
  --assume-role-policy-document file://trust-policy.json \
  --output json
```

#### Validate
```bash
aws iam get-role --role-name "{{user.role_name}}" --output json
```

### Operation: Attach Policy to Role

#### Execute — CLI
```bash
aws iam attach-role-policy \
  --role-name "{{user.role_name}}" \
  --policy-arn "{{user.policy_arn}}" \
  --output json
```

### Operation: Create Access Key (Sensitive)

**Safety Gate**: MUST warn user about credential handling.
> "Access Key will be generated. Store credentials securely—do NOT commit to code."

#### Execute — CLI
```bash
aws iam create-access-key --user-name "{{user.user_name}}" --output json
```

#### Present to User
| Field | JSON Path | Notes |
|-------|-----------|-------|
| AccessKeyId | `.AccessKey.AccessKeyId` | Public identifier |
| SecretAccessKey | `.AccessKey.SecretAccessKey` | **SHOW ONCE only; user must save immediately** |
| Status | `.AccessKey.Status` | Active/Inactive |

### Operation: Delete User (Destructive)

**Safety Gate**: MUST obtain explicit confirmation.
> "Delete user {{user.user_name}} and all associated access keys, policies? IRREVERSIBLE."

#### Pre-flight
- List attached policies
- List access keys
- List group memberships

#### Execute — CLI
```bash
# Detach policies first
aws iam list-attached-user-policies --user-name "{{user.user_name}}" --output json | jq -r '.AttachedPolicies[].PolicyArn' | xargs -I {} aws iam detach-user-policy --user-name "{{user.user_name}}" --policy-arn {}

# Delete access keys
aws iam list-access-keys --user-name "{{user.user_name}}" --output json | jq -r '.AccessKeyMetadata[].AccessKeyId' | xargs -I {} aws iam delete-access-key --user-name "{{user.user_name}}" --access-key-id {}

# Remove from groups
aws iam list-groups-for-user --user-name "{{user.user_name}}" --output json | jq -r '.Groups[].GroupName' | xargs -I {} aws iam remove-user-from-group --user-name "{{user.user_name}}" --group-name {}

# Delete user
aws iam delete-user --user-name "{{user.user_name}}" --output json
```

### Operation: List Users

#### Execute — CLI
```bash
aws iam list-users --output json
```

## IAM Policy Types

| Type | Description | Use Case |
|------|-------------|----------|
| Identity-based | Attach to user/group/role | Grant permissions to identities |
| Resource-based | Attach to resource (S3, Lambda) | Grant permissions to principals |
| Managed (AWS) | Pre-built by AWS | Common permissions (ReadOnly, Admin) |
| Managed (Customer) | Custom reusable policies | Organization-specific |
| Inline | Embedded in identity | One-off permissions |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)