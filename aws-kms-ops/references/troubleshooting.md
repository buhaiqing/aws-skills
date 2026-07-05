# KMS Troubleshooting

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

| Error Code | Cause | Resolution | Details |
|------------|-------|------------|---------|
| **DisabledException** | Key disabled | `enable-key` | [→](troubleshooting-details/key-state-errors.md) |
| **InvalidKeyState** | PendingDeletion/PendingImport | `cancel-key-deletion` or import | [→](troubleshooting-details/key-state-errors.md) |
| **KMSInvalidStateException** | Operation invalid for state | `describe-key` → state-specific | [→](troubleshooting-details/key-state-errors.md) |
| **NotFoundException** | Wrong key ID/region/deleted | `list-keys`, check region | [→](troubleshooting-details/key-not-found.md) |
| **AccessDeniedException** | IAM/Key policy insufficient | `simulate-principal-policy` | [→](troubleshooting-details/permission-errors.md) |
| **InvalidKeyUsageException** | Operation doesn't match key type | Check `KeyUsage`+`KeySpec` | [→](troubleshooting-details/key-usage-errors.md) |
| **AlreadyExistsException** | Alias already exists | Use different alias or `update-alias` | [→](troubleshooting-details/alias-errors.md) |
| **LimitExceededException** | Quota exceeded | HALT; request increase | - |
| **ThrottlingException** | Rate limit exceeded | Exponential backoff | [→](troubleshooting-details/throttling.md) |
| **MalformedPolicyDocumentException** | Invalid JSON policy | Validate JSON | [→](troubleshooting-details/permission-errors.md) |
| **PolicyLockoutSafetyCheck** | Policy removes all admin | Keep root or bypass | [→](troubleshooting-details/permission-errors.md) |
| **DependencyTimeoutException** | CloudHSM timeout | RETRY max 3x | [→](troubleshooting-details/dependency-errors.md) |
| **IncorrectKeyMaterialException** | Import format wrong | Verify 256-bit key | [→](troubleshooting-details/import-errors.md) |
| **ExpiredImportTokenException** | Import token expired | Re-run `get-parameters-for-import` | [→](troubleshooting-details/import-errors.md) |
| **InvalidGrantIdException** | Grant ID wrong/retired | `list-grants` | [→](troubleshooting-details/grant-errors.md) |
| **InvalidGrantTokenException** | Grant token expired | Create new grant | [→](troubleshooting-details/grant-errors.md) |
| **CloudHSMClusterNotActiveException** | Cluster not active | `describe-clusters` | [→](troubleshooting-details/dependency-errors.md) |

## Key Type Compatibility

| Key Type | Valid Operations | Invalid Operations |
|----------|-----------------|-------------------|
| Symmetric | Encrypt, Decrypt, GenerateDataKey | Sign, Verify |
| RSA (Encrypt) | Encrypt, Decrypt | Sign, Verify |
| RSA (Sign) | Sign, Verify | Encrypt, Decrypt |
| ECC | Sign, Verify | Encrypt, Decrypt |

## Key Deletion Flow

| Step | Command | Notes |
|------|---------|-------|
| 1. Check dependencies | `get-key-policy` → filter `.Statement[] \| select(.Principal.Service)` | Common: S3, EBS, RDS, Secrets Manager, Lambda |
| 2. Update dependents | Switch to different key | Wait for propagation |
| 3. Schedule deletion | `schedule-key-deletion --pending-window-in-days 30` | Min 7 days recommended |
| 4. Monitor | CloudTrail `lookup-events` for errors | During pending period |
| 5. Cancel if needed | `cancel-key-deletion` | Only before deletion date |

**Detailed:** [Key Deletion Dependencies](troubleshooting-details/dependency-errors.md)

## Throttling Resolution

| Key Type | Rate Limit | Mitigation |
|----------|-----------|------------|
| Symmetric | ~10,000 req/s | Usually sufficient |
| RSA_2048 | ~500 ops/s | Cache decrypted data keys |
| RSA_3072 | ~100 ops/s | Cache decrypted data keys |
| ECC | ~1,000+ ops/s | Cache decrypted data keys |

**Detailed:** [Backoff pattern](troubleshooting-details/throttling.md)

## Encryption Context Issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Decrypt fails with correct ciphertext | CloudTrail → check `encryptionContext` | Use exact same context for decrypt |
| Policy denies despite permissions | `get-key-policy` → check `kms:EncryptionContext:*` conditions | Match context to policy |

**Detailed:** [Encryption Context](troubleshooting-details/encryption-context.md)

## Cross-Account Access

| Requirement | Where | Policy Element |
|-------------|-------|----------------|
| Key policy allows cross-account | Owning account | `Principal: arn:aws:iam::{{other_account}}:root` + `kms:CreateGrant` etc. |
| IAM policy allows key usage | External account | `kms:Encrypt/Decrypt/GenerateDataKey*` on key ARN |

**Detailed:** [Cross-Account Setup](troubleshooting-details/cross-account.md)

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

## P3 Maintenance Scripts

```bash
# Find keys missing Environment tag
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  tags=$(aws kms list-resource-tags --key-id "$key_id" --query "Tags[?TagKey=='Environment']" --output text)
  [ -z "$tags" ] && echo "MISSING_ENV_TAG: $key_id"
done

# Find orphaned aliases (alias → deleted key)
for alias in $(aws kms list-aliases --query "Aliases[].AliasName" --output text); do
  target_key=$(aws kms list-aliases --query "Aliases[?AliasName=='$alias'].TargetKeyId" --output text)
  key_exists=$(aws kms describe-key --key-id "$target_key" --query "KeyMetadata.KeyState" --output text 2>/dev/null || echo "NOT_FOUND")
  [ "$key_exists" = "NOT_FOUND" ] && echo "ORPHANED_ALIAS: $alias -> $target_key"
done

# Find keys with empty description
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  desc=$(aws kms describe-key --key-id "$key_id" --query "KeyMetadata.Description" --output text)
  [ -z "$desc" ] && echo "NO_DESCRIPTION: $key_id"
done

# Audit grants near limit (500/key)
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  grant_count=$(aws kms list-grants --key-id "$key_id" --query "Grants | length" --output text)
  [ "$grant_count" -gt 400 ] && echo "HIGH_GRANT_COUNT: $key_id has $grant_count grants"
done
```
