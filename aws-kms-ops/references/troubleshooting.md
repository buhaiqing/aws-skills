# KMS Troubleshooting

Common KMS error codes, RCA decision matrix, recovery procedures, and operational monitoring.

## Quick RCA Decision Matrix

| Error | Key State | Decision | SLA | Action |
|-------|-----------|----------|-----|--------|
| DisabledException | Disabled | [AUTO_HEAL] | P0 | `enable-key` |
| InvalidKeyState | PendingDeletion | [AUTO_HEAL] | P0 | `cancel-key-deletion` |
| AccessDeniedException | Enabled | [MANUAL] | P2 | Review IAM/Key Policy |
| ThrottlingException | Enabled | [AI_ASSIST] | P2 | Implement caching/backoff |
| NotFoundException | N/A | HALT | - | Verify key ID/region |
| InvalidKeyUsageException | Enabled | [MANUAL] | P2 | Check key spec matches operation |
| UnusedKey (90d+) | Enabled | [AI_ASSIST] | P3 | Review/delete idle key |
| MissingEnvTags | Enabled | [AI_ASSIST] | P3 | Apply standard tags |
| OrphanedAlias | N/A | [AI_ASSIST] | P3 | Clean up stale alias |
| GrantCountNearLimit | Enabled | [AI_ASSIST] | P3 | Audit retired grants |
| EmptyDescription | Enabled | [AI_ASSIST] | P3 | Document key purpose |

## Error Code Reference

### Compact Error Table

| Error Code | Cause | Resolution |
|------------|-------|------------|
| **DisabledException** | Key disabled | [AUTO_HEAL] `enable-key` |
| **InvalidKeyState** | Key in PendingDeletion/PendingImport | Check state → cancel deletion or import material |
| **KMSInvalidStateException** | Operation invalid for state | `describe-key` → check state-specific actions |
| **NotFoundException** | Wrong key ID/region/deleted | Verify with `list-keys`, check region |
| **AccessDeniedException** | IAM/Key policy insufficient | [MANUAL] Simulate policy + review key policy |
| **InvalidKeyUsageException** | Operation doesn't match key type | Check `KeyUsage`+`KeySpec` match operation |
| **AlreadyExistsException** | Alias already exists | Use different alias or `update-alias` |
| **LimitExceededException** | Quota exceeded | HALT; request increase |
| **ThrottlingException** | Rate limit exceeded | [AI_ASSIST] Exponential backoff; cache data keys |
| **MalformedPolicyDocumentException** | Invalid JSON policy | Validate JSON; check required root access |
| **PolicyLockoutSafetyCheck** | Policy removes all admin | Must keep root access or use `--bypass-policy-lockout-safety-check` |
| **DependencyTimeoutException** | CloudHSM timeout | RETRY max 3x; check cluster status |
| **IncorrectKeyMaterialException** | Import format wrong | Verify 256-bit key, correct wrapping |
| **ExpiredImportTokenException** | Import token expired (>24h) | Re-run `get-parameters-for-import` |

## Detailed Recovery Procedures

### Key State Errors

#### DisabledException
```
Error: Key {{key_id}} is disabled
```
**Cause**: Key has been disabled, cannot be used for operations.
**Impact**: Encryption/decryption operations fail.
**Resolution**:
```bash
# Check key state
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.KeyState"

# Re-enable key
aws kms enable-key --key-id {{key_id}}

# Verify
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.Enabled"
```

#### InvalidKeyState
```
Error: Key {{key_id}} is in an invalid state: PendingDeletion
```
**Cause**: Key is scheduled for deletion or other non-operational state.
**Common States:**
- PendingDeletion: Scheduled for deletion
- PendingImport: Waiting for key material import
- Unavailable: CloudHSM issue

**Resolution**:
```bash
# Check key state
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.KeyState"

# If PendingDeletion - can cancel
deletion_date=$(aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.DeletionDate" --output text)

if [ -n "$deletion_date" ]; then
  echo "Key scheduled for deletion on $deletion_date"
  echo "Run: aws kms cancel-key-deletion --key-id {{key_id}}"
fi

# Cancel deletion
aws kms cancel-key-deletion --key-id {{key_id}}
```

#### KMSInvalidStateException
```
Error: Request cannot be fulfilled due to key state
```
**Cause**: Operation not valid for current key state.

**Resolution:**
```bash
# Get full key status
aws kms describe-key --key-id {{key_id}}

# Check for specific issues:
# - PendingImport: Import key material
# - Unavailable: Check CloudHSM status
```

### Key Not Found Errors

#### NotFoundException
```
Error: Key {{key_id}} does not exist
```
**Cause**: Key ID incorrect, deleted, or wrong region.

**Resolution**:
```bash
# List keys to verify existence
aws kms list-keys --output json

# Check if alias exists
aws kms list-aliases --query "Aliases[?AliasName=='alias/{{key_name}}']"

# Try with full ARN format
aws kms describe-key \
  --key-id arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}

# Check correct region
aws kms describe-key --key-id {{key_id}} --region {{correct_region}}
```

### Permission Errors

#### AccessDeniedException
```
Error: User not authorized to perform operation on key
```
**Cause**: IAM permissions or key policy insufficient.

**Resolution - IAM Policy Check**:
```bash
# Check current IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{{account_id}}:user/{{username}} \
  --action-names kms:Encrypt kms:Decrypt kms:DescribeKey \
  --resource-arns arn:aws:kms:{{region}}:{{account_id}}:key/{{key_id}}

# Required IAM policy actions
# kms:DescribeKey (for key lookup)
# kms:Encrypt (for encryption)
# kms:Decrypt (for decryption)
# kms:GenerateDataKey (for data key generation)
```

**Resolution - Key Policy Check**:
```bash
# Get key policy
aws kms get-key-policy \
  --key-id {{key_id}} \
  --policy-name default \
  --query Policy --output text

# Example fix - add IAM user permissions
# Update policy to include:
{
  "Sid": "Allow IAM User",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::{{account_id}}:user/{{username}}"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}

# Update policy
aws kms put-key-policy \
  --key-id {{key_id}} \
  --policy-name default \
  --policy file://updated-policy.json
```

### Key Usage Errors

#### InvalidKeyUsageException
```
Error: Key usage does not match requested operation
```
**Cause**: Attempting operation not valid for key type.

**Common Mismatches:**

| Key Type | Valid Operations | Invalid Operations |
|----------|-----------------|-------------------|
| Symmetric | Encrypt, Decrypt, GenerateDataKey | Sign, Verify |
| RSA (Encrypt) | Encrypt, Decrypt | Sign, Verify |
| RSA (Sign) | Sign, Verify | Encrypt, Decrypt |
| ECC | Sign, Verify | Encrypt, Decrypt |

**Resolution**:
```bash
# Check key usage
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.{Usage:KeyUsage,Spec:KeySpec}"

# For sign/verify only, create new key
aws kms create-key \
  --key-usage SIGN_VERIFY \
  --key-spec ECC_NIST_P256 \
  --description "Key for signing"
```

### Grant Errors

#### InvalidGrantIdException
```
Error: Grant {{grant_id}} does not exist
```
**Cause**: Grant ID incorrect or already retired.

**Resolution**:
```bash
# List grants for key
aws kms list-grants --key-id {{key_id}}

# Verify grant exists
aws kms list-grants --key-id {{key_id}} \
  --query "Grants[?GrantId=='{{grant_id}}']"
```

#### InvalidGrantTokenException
```
Error: Grant token is invalid or has been retired
```
**Cause**: Grant token expired, revoked, or key deleted.

**Resolution**:
```bash
# Create new grant
aws kms create-grant \
  --key-id {{key_id}} \
  --grantee-principal {{grantee}} \
  --operations Encrypt Decrypt \
  --name {{grant_name}}
```

### Alias Errors

#### AlreadyExistsException (Alias)
```
Error: Alias alias/{{name}} already exists
```
**Cause**: Alias name already in use.

**Resolution**:
```bash
# Check existing alias
aws kms list-aliases --query "Aliases[?AliasName=='alias/{{name}}']"

# Use different name
# Or update alias to point to new key
aws kms update-alias \
  --alias-name alias/{{name}} \
  --target-key-id {{new_key_id}}
```

#### NotFoundException (Alias)
```
Error: Alias does not exist
```
**Cause**: Typo in alias name.

**Resolution**:
```bash
# List all aliases
aws kms list-aliases

# Search for similar names
aws kms list-aliases --query "Aliases[?contains(AliasName, '{{name}}')]"
```

### Import Key Material Errors

#### IncorrectKeyMaterialException
```
Error: Key material does not match expected format
```
**Cause**: Wrapped key material incorrect.

**Resolution**:
```bash
# Get import parameters
aws kms get-parameters-for-import \
  --key-id {{key_id}} \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_2048 \
  --output json

# Verify:
# 1. Key material is 256-bit (32 bytes)
# 2. Wrapped with correct public key
# 3. Using correct algorithm
# 4. Base64 encoded correctly
```

#### ExpiredImportTokenException
```
Error: Import token has expired
```
**Cause**: Token valid for 24 hours only.

**Resolution**:
```bash
# Get new import token
aws kms get-parameters-for-import \
  --key-id {{key_id}} \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_2048
```

### Policy Errors

#### MalformedPolicyDocumentException
```
Error: Key policy JSON is malformed
```
**Cause**: Invalid JSON or policy structure.

**Common Issues:**
- Missing quotes
- Invalid JSON escape sequences
- Missing brackets
- Invalid principal format

**Resolution**:
```bash
# Validate JSON
python3 -c "import json; json.load(open('policy.json'))"

# Check required elements:
# - Version: "2012-10-17"
# - Statement array
# - Effect: "Allow" or "Deny"
# - Principal with valid ARN
# - Action array
# - Resource (usually "*" for KMS)
```

#### PolicyLockoutSafetyCheck
```
Error: Policy would lock out key administrator
```
**Cause**: Policy removes all admin access.

**Resolution**:
```bash
# Must keep at least root access:
{
  "Sid": "Enable IAM User Permissions",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::{{account_id}}:root"
  },
  "Action": "kms:*",
  "Resource": "*"
}

# Or bypass check (DANGEROUS)
aws kms put-key-policy \
  --key-id {{key_id}} \
  --policy-name default \
  --policy '{{user.Policy}}' \
  --bypass-policy-lockout-safety-check
```

### Dependency Errors

#### DependencyTimeoutException
```
Error: Dependent service timeout
```
**Cause**: CloudHSM or other dependency timeout.

**Resolution**:
```bash
# Retry with exponential backoff
# Check CloudHSM cluster status (if using custom key store)

# Check CloudHSM
aws cloudhsmv2 describe-clusters

# Verify cluster state is ACTIVE
aws cloudhsmv2 describe-clusters \
  --query "Clusters[?ClusterId=='{{cluster_id}}'].State"
```

#### CloudHSMClusterNotActiveException
```
Error: CloudHSM cluster is not in ACTIVE state
```
**Cause**: CloudHSM cluster initializing or failed.

**Resolution**:
```bash
# Check cluster status
aws cloudhsmv2 describe-clusters --cluster-id {{cluster_id}}

# Wait for ACTIVE state
# Or initialize if needed
aws cloudhsmv2 initialize-cluster --cluster-id {{cluster_id}
```

## Key Deletion Issues

### Cannot Delete Key (Dependencies)

#### Symptoms
- Key has dependent resources
- Deletion fails or warns

#### Diagnosis
```bash
# Check key usage in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue={{key_id}} \
  --start-time "2024-01-01T00:00:00Z" \
  --output json

# Check service integrations
aws kms get-key-policy --key-id {{key_id}} \
  --query "Policy" --output text | jq '.Statement[] | select(.Principal.Service)'

# Common dependent services:
# - S3 buckets with SSE-KMS
# - EBS volumes
# - RDS databases
# - Secrets Manager secrets
# - Lambda environment variables
```

#### Resolution
```bash
# 1. Identify dependent resources
# 2. Update to use different key
# 3. Wait for completion
# 4. Schedule deletion with long pending window

aws kms schedule-key-deletion \
  --key-id {{key_id}} \
  --pending-window-in-days 30

# Monitor for errors during pending period
```

### Cancel Key Deletion Failed

#### Symptoms
- Key in PendingDeletion
- Cancel operation fails

#### Resolution
```bash
# Verify key state
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.{State:KeyState,DeletionDate:DeletionDate}"

# Cancel deletion
aws kms cancel-key-deletion --key-id {{key_id}}

# If past deletion date, key is permanently deleted
# Cannot recover - must restore from backup using different key
```

## Throttling Issues

### API Throttling

#### Symptoms
- Frequent ThrottlingException
- Requests rejected
- Performance degradation

#### Diagnosis
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/KMS \
  --metric-name ThrottledRequests \
  --dimensions Name=KeyId,Value={{key_id}} \
  --start-time "2024-01-01T00:00:00Z" \
  --end-time "2024-01-31T23:59:59Z" \
  --period 3600 \
  --statistics Sum
```

#### Resolution
```python
# Implement retry with exponential backoff
import time
import random

def retry_with_backoff(operation, max_retries=10):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                delay = min(2 ** attempt * 0.1 + random.uniform(0, 0.5), 60)
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### Request Quota Optimization

#### Symmetric Keys
- **10,000+ requests/second** per key
- Usually sufficient for most workloads

#### Asymmetric Keys
- **RSA_2048**: ~500 ops/sec
- **RSA_3072**: ~100 ops/sec
- **ECC**: ~1,000+ ops/sec

**Resolution**: Cache decrypted data keys for envelope encryption.

## Encryption Context Issues

### Context Mismatch

#### Symptoms
- Decrypt operation fails
- Even with correct ciphertext

#### Diagnosis
```bash
# Check encryption context in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Encrypt \
  --start-time "2024-01-01T00:00:00Z" \
  --output json | \
  jq '.Events[].CloudTrailEvent | fromjson | select(.requestParameters.keyId=="{{key_id}}") | .requestParameters.encryptionContext'
```

#### Resolution
```python
# Must use same encryption context for decrypt
response = kms.decrypt(
    CiphertextBlob=ciphertext,
    EncryptionContext={
        'service': 'myapp',
        'environment': 'prod'
        # Must match exactly
    }
)
```

### Context Access Denied

#### Symptoms
- Policy denies decrypt despite permissions
- Encryption context condition not met

#### Resolution
```bash
# Check key policy for context conditions
aws kms get-key-policy --key-id {{key_id}} --query "Policy"

# Policy might have:
"Condition": {
  "StringEquals": {
    "kms:EncryptionContext:service": "expected-value"
  }
}

# Ensure context matches policy
```

## Cross-Account Access Issues

### Grant Creation Failed

#### Symptoms
- Cannot create cross-account grant
- Access denied

#### Resolution
```bash
# Key policy must allow cross-account access
{
  "Sid": "Allow Cross-Account Grants",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::{{other_account_id}}:root"
  },
  "Action": [
    "kms:CreateGrant",
    "kms:ListGrants",
    "kms:RevokeGrant",
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}
```

### External Account Cannot Use Key

#### Symptoms
- External account operations fail
- "Not authorized" errors

#### Resolution
```bash
# Both policies required:

# 1. Key policy (in owning account)
{
  "Sid": "Allow External Account",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::{{external_account_id}}:root"
  },
  "Action": "kms:*",
  "Resource": "*"
}

# 2. IAM policy (in external account)
{
  "Effect": "Allow",
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:GenerateDataKey*"
  ],
  "Resource": "arn:aws:kms:{{region}}:{{owning_account_id}}:key/{{key_id}}"
}
```

## Recovery Procedures

### Recovery Flow
```
1. Identify error → Check state → Apply decision
2. [AUTO_HEAL]: Disabled/PendingDeletion → Auto-fix
3. [MANUAL]: Access/Policy issues → Human review
4. [AI_ASSIST]: Throttling/Optimization → Recommend
5. Max 3 retries for transient errors
6. HALT for quota/permanent errors
```

### Prevention (Key Deletion)
```
- Use 30-day pending window minimum
- Monitor deletion schedules via CloudTrail
- Require MFA for deletion operations
- Maintain backup keys for critical data
```

## Monitoring Checklist (AIOps)

| Metric | Source | Warning | Critical | Decision |
|--------|--------|---------|----------|----------|
| KeyState | `describe-key` | Disabled | PendingDeletion | [AUTO_HEAL] |
| ThrottledRequests | CloudWatch | >100/hr | >1000/hr | [AI_ASSIST] |
| PendingDeletionWindow | `describe-key` | <7 days | <1 day | [AUTO_HEAL] |
| GrantsCount | `list-grants` | >400 | >490 | [AI_ASSIST] |
| LastRotation | `get-key-rotation-status` | >400 days | Never | [AUTO_HEAL] |
| KeyUsage | CloudTrail | No usage 90d | No usage 180d | [AI_ASSIST] |
| PolicyChanges | CloudTrail | Any change | Deny all added | [MANUAL] |
| MissingTags | `list-resource-tags` | No Env tag | No tags at all | [AI_ASSIST] P3 |
| OrphanedAliases | `list-aliases` | Alias w/o key | - | [AI_ASSIST] P3 |
| EmptyDescription | `describe-key` | No description | - | [AI_ASSIST] P3 |

### CloudTrail/CloudWatch Integration

```bash
# Monitor key security events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DisableKey \
  --start-time $(date -d '-24 hours' -u +%Y-%m-%dT%H:%M:%SZ)

# Check API throttling
aws cloudwatch get-metric-statistics \
  --namespace AWS/KMS \
  --metric-name ThrottledRequests \
  --statistics Sum --period 3600 \
  --start-time $(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z)

# Find unused keys (no decrypt in 90 days)
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  usage=$(aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceName,AttributeValue=$key_id \
    --start-time $(date -d '-90 days' -u +%Y-%m-%dT00:00:00Z) \
    --query "Events[?EventName=='Decrypt']" --output text)
  [ -z "$usage" ] && echo "UNUSED: $key_id"
done
```

## P3 Maintenance Tasks (Low Priority)

### Find Keys Missing Environment Tags
```bash
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  tags=$(aws kms list-resource-tags --key-id "$key_id" --query "Tags[?TagKey=='Environment']" --output text)
  [ -z "$tags" ] && echo "MISSING_ENV_TAG: $key_id"
done
```

### Find Orphaned Aliases (alias pointing to deleted key)
```bash
for alias in $(aws kms list-aliases --query "Aliases[].AliasName" --output text); do
  target_key=$(aws kms list-aliases --query "Aliases[?AliasName=='$alias'].TargetKeyId" --output text)
  if [ -n "$target_key" ]; then
    key_exists=$(aws kms describe-key --key-id "$target_key" --query "KeyMetadata.KeyState" --output text 2>/dev/null || echo "NOT_FOUND")
    [ "$key_exists" = "NOT_FOUND" ] && echo "ORPHANED_ALIAS: $alias -> $target_key"
  fi
done
```

### Find Keys with Empty Description
```bash
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  desc=$(aws kms describe-key --key-id "$key_id" --query "KeyMetadata.Description" --output text)
  [ -z "$desc" ] && echo "NO_DESCRIPTION: $key_id"
done
```

### Audit Grants Near Limit (500 per key)
```bash
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  grant_count=$(aws kms list-grants --key-id "$key_id" --query "Grants | length" --output text)
  [ "$grant_count" -gt 400 ] && echo "HIGH_GRANT_COUNT: $key_id has $grant_count grants"
done
```