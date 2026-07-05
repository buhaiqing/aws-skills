# KMS Key State Errors — Detailed Recovery

## DisabledException

Key is disabled; encryption/decryption operations fail.

```bash
# Check key state
aws kms describe-key --key-id {{key_id}} --query "KeyMetadata.KeyState"

# Re-enable key
aws kms enable-key --key-id {{key_id}}

# Verify
aws kms describe-key --key-id {{key_id}} --query "KeyMetadata.Enabled"
```

## InvalidKeyState

Key in PendingDeletion/PendingImport/Unavailable state.

```bash
# Check key state + deletion date
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.{State:KeyState,DeletionDate:DeletionDate}"

# If PendingDeletion — cancel
aws kms cancel-key-deletion --key-id {{key_id}}
```

**Common States:**
| State | Meaning | Action |
|-------|---------|--------|
| PendingDeletion | Scheduled for deletion | `cancel-key-deletion` |
| PendingImport | Waiting for key material | Import key material |
| Unavailable | CloudHSM issue | Check cluster status |

## KMSInvalidStateException

Operation not valid for current key state.

```bash
# Get full key status
aws kms describe-key --key-id {{key_id}}
# Check for PendingImport, Unavailable, etc.
```
