# KMS Encryption Context Issues — Detailed Recovery

## Context Mismatch

Decrypt fails even with correct ciphertext.

```bash
# Check encryption context in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Encrypt \
  --start-time "2024-01-01T00:00:00Z" | \
  jq '.Events[].CloudTrailEvent | fromjson | select(.requestParameters.keyId=="{{key_id}}") | .requestParameters.encryptionContext'
```

**Resolution:** Must use exact same encryption context for decrypt:
```python
response = kms.decrypt(
    CiphertextBlob=ciphertext,
    EncryptionContext={'service': 'myapp', 'environment': 'prod'}  # Must match exactly
)
```

## Context Access Denied

Policy denies decrypt despite permissions.

```bash
# Check key policy for context conditions
aws kms get-key-policy --key-id {{key_id}} --query "Policy"

# Policy might have:
"Condition": {"StringEquals": {"kms:EncryptionContext:service": "expected-value"}}

# Ensure context matches policy
```
