# KMS Key Usage Errors — Detailed Recovery

## InvalidKeyUsageException

Attempting operation not valid for key type.

```bash
# Check key usage
aws kms describe-key --key-id {{key_id}} \
  --query "KeyMetadata.{Usage:KeyUsage,Spec:KeySpec}"

# For sign/verify only, create new key
aws kms create-key --key-usage SIGN_VERIFY --key-spec ECC_NIST_P256
```

**Key Type Compatibility:**
| Key Type | Valid Operations | Invalid Operations |
|----------|-----------------|-------------------|
| Symmetric | Encrypt, Decrypt, GenerateDataKey | Sign, Verify |
| RSA (Encrypt) | Encrypt, Decrypt | Sign, Verify |
| RSA (Sign) | Sign, Verify | Encrypt, Decrypt |
| ECC | Sign, Verify | Encrypt, Decrypt |
