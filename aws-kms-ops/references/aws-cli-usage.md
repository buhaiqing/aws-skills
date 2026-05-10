# AWS CLI Usage - KMS

AWS CLI commands for KMS operations. All commands use `--output json`.

## Key Operations

### Create Key
```bash
# Create symmetric encryption key (default)
aws kms create-key \
  --description "{{user.KeyDescription}}" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --origin AWS_KMS \
  --policy '{{user.KeyPolicy}}' \
  --tags TagKey=Environment,TagValue=production \
  --output json

# Create RSA key for asymmetric encryption
aws kms create-key \
  --description "{{user.KeyDescription}}" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec RSA_2048 \
  --origin AWS_KMS \
  --output json

# Create RSA key for signing
aws kms create-key \
  --description "{{user.KeyDescription}}" \
  --key-usage SIGN_VERIFY \
  --key-spec RSA_2048 \
  --origin AWS_KMS \
  --output json
```

**JSON paths:**
- `.KeyMetadata.KeyId` → unique key ID (UUID format)
- `.KeyMetadata.KeyArn` → full ARN
- `.KeyMetadata.KeyState` → "Creating" → "Enabled"
- `.KeyMetadata.KeyUsage` → ENCRYPT_DECRYPT, SIGN_VERIFY
- `.KeyMetadata.KeySpec` → SYMMETRIC_DEFAULT, RSA_2048, etc.
- `.KeyMetadata.AwsAccountId` → account ID

### Describe Key
```bash
aws kms describe-key \
  --key-id {{user.KeyId}} \
  --output json
```

**KeyId formats accepted:**
- Key ID: `1234abcd-12ab-34cd-56ef-1234567890ab`
- Key ARN: `arn:aws:kms:us-east-1:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab`
- Alias: `alias/my-key`
- Alias ARN: `arn:aws:kms:us-east-1:123456789012:alias/my-key`

**JSON paths:**
- `.KeyMetadata.KeyId` → key ID
- `.KeyMetadata.KeyState` → "Enabled", "Disabled", "PendingDeletion", "PendingImport", "Unavailable"
- `.KeyMetadata.Enabled` → boolean
- `.KeyMetadata.DeletionDate` → scheduled deletion time (if pending deletion)
- `.KeyMetadata.KeyManager` → "CUSTOMER" or "AWS"
- `.KeyMetadata.Description` → description
- `.KeyMetadata.CreationDate` → timestamp
- `.KeyMetadata.MultiRegion` → boolean
- `.KeyMetadata.MultiRegionConfiguration` → multi-region details

### List Keys
```bash
# List all keys
aws kms list-keys --output json

# With aliases
aws kms list-aliases \
  --query "Aliases[?starts_with(AliasName, 'alias/{{user.Prefix}}')]" \
  --output json
```

**JSON paths:**
- `.Keys[].KeyId` → key IDs
- `.Keys[].KeyArn` → key ARNs

### Update Key Description
```bash
aws kms update-key-description \
  --key-id {{user.KeyId}} \
  --description "{{user.NewDescription}}" \
  --output json
```

### Enable Key
```bash
aws kms enable-key \
  --key-id {{user.KeyId}} \
  --output json
```

### Disable Key
```bash
aws kms disable-key \
  --key-id {{user.KeyId}} \
  --output json
```

**Warning:** Disabling a key affects all services using it.

### Schedule Key Deletion
```bash
aws kms schedule-key-deletion \
  --key-id {{user.KeyId}} \
  --pending-window-in-days 30 \
  --output json
```

**Safety Gate:** Human confirmation required.

**pending-window-in-days:**
- Minimum: 7 days
- Maximum: 30 days (default)
- Cannot be changed after scheduling

**JSON paths:**
- `.KeyId` → key ID
- `.DeletionDate` → actual deletion date

### Cancel Key Deletion
```bash
aws kms cancel-key-deletion \
  --key-id {{user.KeyId}} \
  --output json
```

## Key Rotation

### Enable Key Rotation
```bash
aws kms enable-key-rotation \
  --key-id {{user.KeyId}} \
  --output json
```

### Disable Key Rotation
```bash
aws kms disable-key-rotation \
  --key-id {{user.KeyId}} \
  --output json
```

### Get Key Rotation Status
```bash
aws kms get-key-rotation-status \
  --key-id {{user.KeyId}} \
  --output json
```

**JSON paths:**
- `.KeyRotationEnabled` → boolean

**Rotation characteristics:**
- Symmetric keys: Automatic annual rotation
- Asymmetric keys: Manual rotation only
- Existing data remains usable
- New encryption uses new key material

## Alias Operations

### Create Alias
```bash
aws kms create-alias \
  --alias-name alias/{{user.AliasName}} \
  --target-key-id {{user.KeyId}} \
  --output json
```

**Alias naming rules:**
- Must start with `alias/`
- 1-256 alphanumeric characters
- Can include forward slashes for hierarchies: `alias/prod/app1/key`

### Update Alias
```bash
aws kms update-alias \
  --alias-name alias/{{user.AliasName}} \
  --target-key-id {{user.NewKeyId}} \
  --output json
```

**Use case:** Point alias to new key (key rotation scenario).

### List Aliases
```bash
# All aliases
aws kms list-aliases --output json

# For specific key
aws kms list-aliases \
  --key-id {{user.KeyId}} \
  --output json

# Filter by prefix
aws kms list-aliases \
  --query "Aliases[?starts_with(AliasName, 'alias/prod/')]" \
  --output json
```

**JSON paths:**
- `.Aliases[].AliasName` → alias name
- `.Aliases[].AliasArn` → alias ARN
- `.Aliases[].TargetKeyId` → target key ID

### Delete Alias
```bash
aws kms delete-alias \
  --alias-name alias/{{user.AliasName}} \
  --output json
```

**Note:** Deleting alias does not delete the key.

## Key Policy Operations

### Get Key Policy
```bash
aws kms get-key-policy \
  --key-id {{user.KeyId}} \
  --policy-name default \
  --output json
```

**JSON paths:**
- `.Policy` → JSON policy document (string)

### Put Key Policy
```bash
aws kms put-key-policy \
  --key-id {{user.KeyId}} \
  --policy-name default \
  --policy '{{user.KeyPolicy}}' \
  --output json
```

### Example Key Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::{{user.AccountId}}:root"
      },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow S3 Service",
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Allow Specific Role",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::{{user.AccountId}}:role/{{user.RoleName}}"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

## Grant Operations

### Create Grant
```bash
aws kms create-grant \
  --key-id {{user.KeyId}} \
  --grantee-principal {{user.GranteePrincipal}} \
  --operations Encrypt Decrypt GenerateDataKey DescribeKey \
  --constraints EncryptionContextSubset={"key":"value"} \
  --name {{user.GrantName}} \
  --output json
```

**JSON paths:**
- `.GrantToken` → grant token
- `.GrantId` → grant ID

### List Grants
```bash
aws kms list-grants \
  --key-id {{user.KeyId}} \
  --output json
```

**JSON paths:**
- `.Grants[].GrantId` → grant ID
- `.Grants[].GranteePrincipal` → grantee
- `.Grants[].Operations[]` → allowed operations
- `.Grants[].Constraints` → encryption context constraints

### Retire Grant
```bash
aws kms retire-grant \
  --key-id {{user.KeyId}} \
  --grant-id {{user.GrantId}} \
  --output json
```

### Revoke Grant
```bash
aws kms revoke-grant \
  --key-id {{user.KeyId}} \
  --grant-id {{user.GrantId}} \
  --output json
```

**Note:** Revoke is immediate, retire is eventual.

## Encrypt/Decrypt Operations

### Encrypt
```bash
aws kms encrypt \
  --key-id {{user.KeyId}} \
  --plaintext "{{user.Plaintext}}" \
  --encryption-context key=value \
  --output json
```

**Plaintext:**
- Max 4096 bytes
- Base64 encoded automatically by CLI
- For larger data, use envelope encryption with data keys

**JSON paths:**
- `.CiphertextBlob` → encrypted data (base64)
- `.KeyId` → key ARN used
- `.EncryptionAlgorithm` → algorithm used

### Decrypt
```bash
aws kms decrypt \
  --ciphertext-blob {{user.Ciphertext}} \
  --encryption-context key=value \
  --output json
```

**JSON paths:**
- `.Plaintext` → decrypted data (base64)
- `.KeyId` → key ARN used for decryption
- `.EncryptionAlgorithm` → algorithm used

### Re-encrypt
```bash
aws kms re-encrypt \
  --ciphertext-blob {{user.Ciphertext}} \
  --destination-key-id {{user.NewKeyId}} \
  --output json
```

**Use case:** Change encryption key without decrypting locally.

## Data Key Operations

### Generate Data Key
```bash
# Symmetric data key
aws kms generate-data-key \
  --key-id {{user.KeyId}} \
  --key-spec AES_256 \
  --encryption-context key=value \
  --output json

# For specific number of bytes
aws kms generate-data-key \
  --key-id {{user.KeyId}} \
  --number-of-bytes 32 \
  --encryption-context key=value \
  --output json
```

**JSON paths:**
- `.CiphertextBlob` → encrypted data key
- `.Plaintext` → plaintext data key (base64) - handle securely!
- `.KeyId` → KMS key used

**Envelope encryption pattern:**
1. Generate data key (Plaintext + CiphertextBlob)
2. Encrypt data locally with plaintext data key
3. Store encrypted data + CiphertextBlob (encrypted data key)
4. Discard plaintext data key from memory
5. To decrypt: decrypt CiphertextBlob with KMS, decrypt data locally

### Generate Data Key Without Plaintext
```bash
aws kms generate-data-key-without-plaintext \
  --key-id {{user.KeyId}} \
  --key-spec AES_256 \
  --output json
```

**Use case:** Generate data key for external systems without exposing plaintext.

### Generate Random
```bash
aws kms generate-random \
  --number-of-bytes 32 \
  --output json
```

**JSON paths:**
- `.Plaintext` → random bytes (base64)

## Key Import Operations

### Get Parameters for Import
```bash
aws kms get-parameters-for-import \
  --key-id {{user.KeyId}} \
  --wrapping-algorithm RSAES_OAEP_SHA_256 \
  --wrapping-key-spec RSA_2048 \
  --output json
```

**JSON paths:**
- `.PublicKey` → public key for wrapping (base64)
- `.ImportToken` → token for import operation

### Import Key Material
```bash
aws kms import-key-material \
  --key-id {{user.KeyId}} \
  --import-token {{user.ImportToken}} \
  --encrypted-key-material {{user.EncryptedKeyMaterial}} \
  --expiration-model KEY_MATERIAL_EXPIRES \
  --valid-to 2025-12-31T23:59:59Z \
  --output json
```

## Multi-Region Key Operations

### Create Multi-Region Key
```bash
aws kms create-key \
  --multi-region \
  --description "{{user.KeyDescription}}" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --output json
```

### Replicate Key
```bash
aws kms replicate-key \
  --key-id {{user.KeyId}} \
  --replica-region us-west-2 \
  --policy '{{user.ReplicaPolicy}}' \
  --description "{{user.ReplicaDescription}}" \
  --output json
```

### Update Primary Region
```bash
aws kms update-primary-region \
  --key-id {{user.KeyId}} \
  --primary-region us-west-2 \
  --output json
```

## Common Options

```bash
--key-id {{user.KeyId}}                    # Key identifier (ID, ARN, alias)
--description "{{user.Description}}"       # Key description
--policy '{{user.Policy}}'                 # Key policy (JSON string)
--tags TagKey=Name,TagValue=value          # Tags
--pending-window-in-days 30                # Deletion waiting period
--key-usage ENCRYPT_DECRYPT                # or SIGN_VERIFY
--key-spec SYMMETRIC_DEFAULT               # or RSA_2048, etc.
--origin AWS_KMS                           # or EXTERNAL, AWS_CLOUDHSM
--bypass-policy-lockout-safety-check       # Advanced use only
```

## Key States

| State | Description | Operations Allowed |
|-------|-------------|-------------------|
| `Enabled` | Key active | All |
| `Disabled` | Key disabled | DescribeKey, EnableKey, ScheduleKeyDeletion |
| `PendingDeletion` | Scheduled for deletion | CancelKeyDeletion, DescribeKey |
| `PendingImport` | Waiting for key material | ImportKeyMaterial, DescribeKey |
| `Unavailable` | Key material unavailable | DescribeKey only |

## Key Usage Patterns

### Symmetric Key (SYMMETRIC_DEFAULT)
- **Use**: General encryption
- **Algorithms**: AES-256-GCM
- **Operations**: Encrypt, Decrypt, GenerateDataKey
- **Rotation**: Automatic annual rotation supported

### Asymmetric RSA Key
n- **Use**: Asymmetric encryption or signing
- **Specs**: RSA_2048, RSA_3072, RSA_4096
- **Operations**: Encrypt/Decrypt or Sign/Verify
- **Rotation**: Manual rotation only

### Asymmetric ECC Key
- **Use**: Digital signatures
- **Specs**: ECC_NIST_P256, ECC_NIST_P384, ECC_SECG_P256K1
- **Operations**: Sign/Verify only
- **Rotation**: Manual rotation only