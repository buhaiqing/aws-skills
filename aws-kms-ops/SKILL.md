# AWS KMS Ops Skill

AWS Key Management Service (KMS) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests KMS key creation, rotation, or deletion
- User needs to enable/disable keys
- User asks about encryption key management
- User mentions "KMS", "encryption key", "data key", "CMK"
- User needs to configure key policies or grants
- User asks about automatic key rotation
- User needs to encrypt/decrypt data or generate data keys
- User mentions "SSE-KMS", "envelope encryption", "key hierarchy"

**SHOULD-NOT activate when:**
- S3 bucket encryption only (use `aws-s3-ops`)
- RDS encryption only (use `aws-rds-ops`)
- EBS volume encryption only (use `aws-ec2-ops`)
- Secrets Manager operations (use `aws-secrets-manager-ops`)

**Delegation:**
- IAM policy editing → `aws-iam-ops` (IAM policies for key access)
- S3 bucket operations → `aws-s3-ops` (bucket encryption config)
- RDS operations → `aws-rds-ops` (database encryption)
- CloudTrail operations → `aws-cloudtrail-ops` (trail encryption)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Key | Yes | None |
| Describe Key | Yes | None |
| List Keys | Yes | None |
| Update Key Description | Yes | None |
| Enable Key | Yes | None |
| Disable Key | Yes | **Warning - affects dependent services** |
| Schedule Key Deletion | Yes | **CRITICAL - data loss risk** |
| Cancel Key Deletion | Yes | None |
| Enable Auto-Rotation | Yes | None |
| Create Alias | Yes | None |
| Delete Alias | Yes | None |
| Put Key Policy | Yes | None |
| Get Key Policy | Yes | None |
| Create Grant | Yes | None |
| Revoke Grant | Yes | None |
| Encrypt | Yes | None |
| Decrypt | Yes | None |
| Generate Data Key | Yes | None |
| Generate Random | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.KeyId}}` | User input | alias/my-key or key-id |
| `{{user.AliasName}}` | User input | alias/production-key |
| `{{user.KeyDescription}}` | User input | Key for production data |
| `{{user.Plaintext}}` | User input | Data to encrypt (max 4KB) |
| `{{user.Ciphertext}}` | User input | Data to decrypt |
| `{{user.GranteePrincipal}}` | User input | IAM role/user ARN |

**Never commit real credentials. Always use `{{env.*}}` or `{{user.*}}` placeholders.**

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
3. Confirm region: aws kms list-keys --region {{env.AWS_DEFAULT_REGION}}
4. Check service quotas: aws service-quotas get-service-quota --service-code kms --quota-code L-...
5. Verify IAM permissions for KMS operations
```

### Execute (Primary: CLI)
```
aws kms create-key \
  --description "{{user.KeyDescription}}" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --origin AWS_KMS \
  --policy '{{user.KeyPolicy}}' \
  --tags TagKey=Environment,TagValue=production \
  --output json
```

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK:
```python
import boto3
kms = boto3.client('kms', region_name='{{env.AWS_DEFAULT_REGION}}')
response = kms.create_key(
    Description='{{user.KeyDescription}}',
    KeyUsage='ENCRYPT_DECRYPT',
    KeySpec='SYMMETRIC_DEFAULT',
    Policy='{{user.KeyPolicy}}'
)
```

### Validate
```
1. Poll status: aws kms describe-key --key-id {{user.KeyId}}
2. Wait for KeyState: Enabled
3. Max wait: Immediate (synchronous)
4. Verify key is usable
```

### Recover
| Error Type | Action |
|------------|---------|
| AlreadyExistsException | HALT - key alias already exists |
| NotFoundException | HALT - key does not exist |
| DisabledException | FIX - enable key first |
| InvalidKeyState | HALT - key in invalid state (PendingDeletion, PendingImport) |
| DependencyTimeoutException | RETRY - temporary service issue, max 3 retries |
| InvalidKeyUsageException | FIX - key not valid for requested operation |
| InvalidGrantIdException | HALT - grant does not exist |
| KMSInvalidStateException | FIX - fix key state before operation |
| LimitExceededException | HALT - quota exceeded, request increase |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Key Deletion (CRITICAL)
```
BEFORE schedule-key-deletion:
1. Display: "Deleting key {{user.KeyId}} will PERMANENTLY destroy key material"
2. WARN: "All data encrypted with this key will be UNRECOVERABLE"
3. REQUIRE: List of dependent services (S3, RDS, EBS, etc.)
4. REQUIRE: Confirmation that backups exist with different keys
5. Ask: "Type 'PERMANENTLY DELETE {{user.KeyId}}' to confirm"
6. Use minimum 7-day pending window (default: 30 days)
7. Proceed only after confirmation matches
```

### Key Disabling
```
BEFORE disable-key:
1. WARN: "Disabling key will break encryption/decryption for dependent services"
2. REQUIRE: List affected services
3. Ask: "Continue? (yes/no)"
4. Proceed only after explicit "yes"
```

### Key Rotation
```
BEFORE enable-key-rotation:
1. INFO: "Rotation generates new key material, old material preserved"
2. INFO: "Existing encrypted data remains usable"
3. Proceed without additional confirmation
```

## Output Convention

Always use `--output json` for agent parsing.

Key JSON paths:
- `.KeyMetadata.KeyId` - unique key ID
- `.KeyMetadata.KeyArn` - full ARN
- `.KeyMetadata.KeyState` - Enabled, Disabled, PendingDeletion, etc.
- `.KeyMetadata.KeyUsage` - ENCRYPT_DECRYPT, SIGN_VERIFY, etc.
- `.KeyMetadata.KeySpec` - SYMMETRIC_DEFAULT, RSA_2048, etc.
- `.KeyMetadata.CreationDate` - timestamp
- `.KeyMetadata.DeletionDate` - scheduled deletion time
- `.KeyMetadata.Enabled` - boolean
- `.KeyMetadata.Description` - key description
- `.KeyMetadata.Origin` - AWS_KMS, EXTERNAL, AWS_CLOUDHSM
- `.KeyMetadata.KeyManager` - CUSTOMER or AWS
- `.CiphertextBlob` - encrypted data (base64)
- `.Plaintext` - decrypted data (base64)
- `.Aliases[].AliasName` - alias name
- `.Grants[].GrantId` - grant ID
- `.GrantTokens[]` - grant tokens for cross-account access

## Related Skills

- `aws-iam-ops` - IAM policies for key access control
- `aws-s3-ops` - S3 SSE-KMS encryption
- `aws-rds-ops` - RDS storage encryption
- `aws-ec2-ops` - EBS volume encryption
- `aws-cloudtrail-ops` - Trail encryption
- `aws-lambda-ops` - Lambda environment variable encryption
- `aws-secrets-manager-ops` - Secrets encryption

## Reference Files

- `references/aws-cli-usage.md` - CLI command reference
- `references/boto3-sdk-usage.md` - Python SDK patterns
- `references/core-concepts.md` - KMS architecture, key types
- `references/troubleshooting.md` - Error codes, recovery procedures
- `assets/example-config.yaml` - Key configuration