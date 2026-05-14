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
---
# AWS Secrets Manager Ops Skill

AWS Secrets Manager operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests secret creation, rotation, or deletion
- User needs to retrieve secret values
- User asks about Secrets Manager
- User needs to configure automatic rotation
- User mentions "secret", "credential", "password", "API key"
- User needs cross-account secret access

**SHOULD-NOT activate when:**
- Parameter Store operations (use `aws-ssm-ops`)
- KMS key operations (use `aws-kms-ops`)

**Delegation:**
- KMS → `aws-kms-ops` (encryption key)
- Lambda → `aws-lambda-ops` (rotation function)
- IAM → `aws-iam-ops` (access policies)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Secret | Yes | None |
| Get Secret Value | Yes | None |
| Update Secret | Yes | None |
| Delete Secret | Yes | **Human confirmation** |
| Restore Secret | Yes | None |
| Rotate Secret | Yes | None |
| Cancel Rotation | Yes | None |
| Replicate Secret | Yes | None |
| Tag Secret | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.SecretId}}` | User input | my-secret-id or ARN |
| `{{user.SecretName}}` | User input | prod/db/password |
| `{{user.SecretString}}` | User input | Secret value (plain text) |
| `{{user.SecretBinary}}` | User input | Binary secret (base64) |
| `{{user.KmsKeyId}}` | User input | alias/aws/secretsmanager |

## Execution Flow

### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

```
3. Check KMS key exists: aws kms describe-key --key-id {{user.KmsKeyId}}
4. Verify IAM permissions for secretsmanager:GetSecretValue
```

### Execute (Primary: CLI)
```
aws secretsmanager create-secret \
  --name {{user.SecretName}} \
  --description "{{user.Description}}" \
  --secret-string '{{user.SecretString}}' \
  --kms-key-id {{user.KmsKeyId}} \
  --output json
```

### Execute (Fallback: boto3)
```python
import boto3
sm = boto3.client('secretsmanager', region_name='{{env.AWS_DEFAULT_REGION}}')
response = sm.create_secret(
    Name='{{user.SecretName}}',
    SecretString='{{user.SecretString}}'
)
```

## Safety Gates

### Secret Deletion
```
BEFORE delete-secret:
1. Display: "Deleting {{user.SecretName}} will remove all versions"
2. Ask: "Type 'DELETE {{user.SecretName}}' to confirm"
3. Require exact confirmation
```

## Output Convention

Key JSON paths:
- `.ARN` - secret ARN
- `.Name` - secret name
- `.VersionId` - current version
- `.SecretString` - secret value (plain text)
- `.SecretBinary` - secret value (base64)
- `.CreatedDate` - creation timestamp
- `.DeletedDate` - deletion timestamp (if pending)

## Related Skills

- `aws-kms-ops` - Encryption key management
- `aws-lambda-ops` - Rotation function
- `aws-iam-ops` - Access policies

## Reference Files

- `references/aws-cli-usage.md`
- `references/boto3-sdk-usage.md`
- `references/core-concepts.md`
- `references/troubleshooting.md`
- `assets/example-config.yaml`