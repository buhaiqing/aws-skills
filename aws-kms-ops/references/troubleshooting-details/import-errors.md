# KMS Import Key Material Errors — Detailed Recovery

## IncorrectKeyMaterialException

Wrapped key material incorrect.

```bash
# Get import parameters
aws kms get-parameters-for-import \
  --key-id {{key_id}} \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_2048

# Verify:
# 1. Key material is 256-bit (32 bytes)
# 2. Wrapped with correct public key
# 3. Using correct algorithm
# 4. Base64 encoded correctly
```

## ExpiredImportTokenException

Import token valid for 24 hours only.

```bash
# Get new import token
aws kms get-parameters-for-import \
  --key-id {{key_id}} \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_2048
```
