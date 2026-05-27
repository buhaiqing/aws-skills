---
name: aws-secretsmanager-ops
description: >-
  Use when the user needs to create, manage, or rotate secrets in AWS Secrets
  Manager (distinct from SSM Parameter Store); store and retrieve sensitive
  information like database credentials, API keys, or OAuth tokens; configure
  automatic secret rotation with Lambda functions; manage cross-account secret
  access; or implement secure credential management for applications, even if they
  don't say "Secrets Manager" and instead say "store my database password
  securely", "manage API keys", "set up credential rotation", "configure secret
  access across accounts", or "handle sensitive configuration in AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Secrets Manager endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---
# AWS Secrets Manager Ops Skill

## Common JSON Paths (Centralized)

```
# Create Secret:     .{ARN,Name,VersionId}
# Get Secret Value:  .{ARN,Name,SecretString,SecretBinary,VersionId}
# Put Secret Value:  .{ARN,Name,VersionId}
# Delete Secret:     .{ARN,Name,DeletionDate}
# Restore Secret:    .{ARN,Name}
# Rotate Secret:     .{ARN,Name,VersionId}
# Replicate Secret:  .{ARN,Name,ReplicationStatus}
```

## Trigger & Scope

### SHOULD Use When
- User requests secret creation, rotation, or deletion
- User needs to retrieve secret values
- User asks about Secrets Manager
- User needs to configure automatic rotation
- User mentions "secret", "credential", "password", "API key"
- User needs cross-account secret access

### SHOULD NOT Use When
- Parameter Store operations → delegate to: `aws-ssm-ops`
- KMS key operations → delegate to: `aws-kms-ops`

### Delegation
- KMS → `aws-kms-ops` (encryption key)
- Lambda → `aws-lambda-ops` (rotation function)
- IAM → `aws-iam-ops` (access policies)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.SecretId}}` | User input | Secret name or ARN |
| `{{user.SecretName}}` | User input | prod/db/password |
| `{{user.SecretString}}` | User input | Secret value (plain text) |
| `{{user.KmsKeyId}}` | User input | alias/aws/secretsmanager |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Check KMS key exists if custom key specified.

**CLI (primary)**: `aws secretsmanager [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-secret-value` to confirm create/update. For delete, verify DeletionDate is set.

**Common Recovery**:
| Error | Action |
|-------|--------|
| ResourceNotFoundException (404) | HALT — verify secret name/ARN |
| InvalidRequestException | HALT — operation not allowed in current state |
| EncryptionFailure | FIX — check KMS key permissions |
| Throttling (429) | Backoff, retry 3x |
| InternalServiceError (5xx) | Retry 3x; HALT |

## Safety Gates

### Secret Deletion
```
⚠️ Deleting {{user.SecretName}} will remove all versions. Default recovery window: 30 days.
Use --force-delete-without-recovery for immediate deletion (no recovery).
Confirm: Type DELETE {{user.SecretName}} to proceed.
```

## Related Skills

- `aws-kms-ops` — Encryption key management
- `aws-lambda-ops` — Rotation function
- `aws-iam-ops` — Access policies

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)