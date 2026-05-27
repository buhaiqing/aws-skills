---
name: aws-kms-ops
description: >-
  Use when the user needs to create, manage, or rotate AWS KMS encryption keys;
  encrypt and decrypt data using AWS-managed keys; configure key policies,
  grants, or aliases; enable automatic key rotation; schedule or cancel key
  deletion; implement envelope encryption with data keys; or integrate SSE-KMS
  with other AWS services, even if they don't say "KMS" and instead say
  "manage encryption keys in AWS", "encrypt my data with AWS keys", "set up
  AWS key rotation", "configure SSE-KMS encryption", or "implement envelope
  encryption with data keys in AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to KMS endpoints.
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
    - AWS_SESSION_TOKEN
---
# AWS KMS Ops Skill

Operational runbook for AWS KMS — key lifecycle, encryption, grants, policies, and rotation.

## Common JSON Paths (Centralized)

```
# Create Key:      .KeyMetadata.{KeyId,KeyArn,KeyState}
# Describe Key:    .KeyMetadata.{KeyState,Enabled,KeyUsage,KeySpec,Description,CreationDate}
# List Keys:       .Keys[].{KeyId,KeyArn}
# Enable/Disable:  Empty (success)
# Schedule Delete: .{KeyId,DeletionDate}
# Encrypt:         .{CiphertextBlob,KeyId}
# Decrypt:         .{Plaintext,KeyId}
# Gen DataKey:     .{CiphertextBlob,Plaintext,KeyId}
# Create Alias:    Empty (success)
# Create Grant:    .{GrantToken,GrantId}
```

## Trigger & Scope

### SHOULD Use When
- User requests KMS key creation, rotation, or deletion
- User needs to enable/disable keys
- User asks about encryption key management
- User mentions "KMS", "encryption key", "data key", "CMK"
- User needs to configure key policies or grants
- User asks about automatic key rotation
- User needs to encrypt/decrypt data or generate data keys
- User mentions "SSE-KMS", "envelope encryption", "key hierarchy"

### SHOULD NOT Use When
- S3 bucket encryption → `aws-s3-ops`
- RDS encryption → `aws-rds-ops`
- EBS volume encryption → `aws-ec2-ops`
- Secrets Manager operations → `aws-secrets-manager-ops`

### Delegation
- IAM policy editing → `aws-iam-ops` (IAM policies for key access)
- S3 bucket ops → `aws-s3-ops` (bucket encryption config)
- RDS ops → `aws-rds-ops` (database encryption)
- CloudTrail ops → `aws-cloudtrail-ops` (trail encryption)

## Placeholder Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | STS temp creds only |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{r.region}}` | User input or env | Default `us-east-1` |
| `{{u.key_id}}` | User input | Key ID, ARN, or `alias/` prefix |
| `{{u.alias}}` | User input | Without `alias/` prefix |
| `{{u.desc}}` | User input | Description for key |
| `{{u.plaintext}}` | User input | Max 4KB for encrypt |
| `{{u.ciphertext}}` | User input | Base64 encoded ciphertext |
| `{{u.grantee}}` | User input | IAM role/user ARN |
| `{{o.*}}` | Last API response | Parse from JSON output |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify region via `list-keys`, check quotas.

**CLI (primary)**: `aws kms [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `describe-key` to confirm state changes (Enabled/Disabled/PendingDeletion). Key operations are synchronous.

**Common Recovery**:
| Error | Action |
|-------|--------|
| AlreadyExistsException | HALT — key alias already exists |
| NotFoundException | HALT — key does not exist |
| DisabledException | FIX — enable key first |
| InvalidKeyState | HALT — key in invalid state |
| DependencyTimeoutException | RETRY max 3x |
| LimitExceededException | HALT — quota exceeded |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Key Deletion (CRITICAL)
```
⚠️ Deleting key {{u.key_id}} will PERMANENTLY destroy key material.
All data encrypted with this key will be UNRECOVERABLE.
Before proceeding:
1. List dependent services (S3, RDS, EBS, etc.)
2. Confirm backups exist with different keys
3. Use minimum 7-day pending window (default: 30 days)
Confirm: Type PERMANENTLY DELETE {{u.key_id}} to proceed.
```

### Key Disabling
```
⚠️ Disabling key will break encryption/decryption for dependent services.
List affected services first. Continue? (yes/no)
```

### Key Rotation
```
ℹ️ Rotation generates new key material. Old material preserved. Existing data remains usable.
```

## Related Skills

- `aws-iam-ops` - IAM policies for key access control
- `aws-s3-ops` - S3 SSE-KMS encryption
- `aws-rds-ops` - RDS storage encryption
- `aws-ec2-ops` - EBS volume encryption
- `aws-cloudtrail-ops` - Trail encryption
- `aws-lambda-ops` - Lambda env var encryption
- `aws-secrets-manager-ops` - Secrets encryption

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)