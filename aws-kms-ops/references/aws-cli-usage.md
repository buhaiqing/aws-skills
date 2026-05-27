# AWS CLI Usage - KMS

AWS CLI commands for KMS operations. All commands use `--region {{r.region}} --output json`.

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

## Key Operations

### Create Key
```bash
# Symmetric encryption (default)
aws kms create-key --description "{{u.desc}}" --key-usage ENCRYPT_DECRYPT --key-spec SYMMETRIC_DEFAULT

# RSA for asymmetric encryption
aws kms create-key --description "{{u.desc}}" --key-usage ENCRYPT_DECRYPT --key-spec RSA_2048

# RSA for signing
aws kms create-key --description "{{u.desc}}" --key-usage SIGN_VERIFY --key-spec RSA_2048

# Multi-region key
aws kms create-key --multi-region --description "{{u.desc}}"
```

### Describe Key
```bash
aws kms describe-key --key-id {{u.key_id}}
```
KeyId accepts: Key ID (UUID), Key ARN, `alias/my-key`, Alias ARN.

### List Keys
```bash
aws kms list-keys
aws kms list-aliases --query "Aliases[?starts_with(AliasName, 'alias/{{u.prefix}}')]"
```

### Enable/Disable/Schedule Delete
```bash
aws kms enable-key --key-id {{u.key_id}}
aws kms disable-key --key-id {{u.key_id}}
aws kms schedule-key-deletion --key-id {{u.key_id}} --pending-window-in-days {{u.days}}    # 7-30 days
aws kms cancel-key-deletion --key-id {{u.key_id}}
```

## Key Rotation
```bash
aws kms enable-key-rotation --key-id {{u.key_id}}
aws kms disable-key-rotation --key-id {{u.key_id}}
aws kms get-key-rotation-status --key-id {{u.key_id}}
```
Rotation: Symmetric=automatic annual, Asymmetric=manual only.

## Alias Operations
```bash
aws kms create-alias --alias-name alias/{{u.alias}} --target-key-id {{u.key_id}}
aws kms update-alias --alias-name alias/{{u.alias}} --target-key-id {{u.new_key_id}}
aws kms list-aliases --key-id {{u.key_id}}
aws kms delete-alias --alias-name alias/{{u.alias}}
```
Alias naming: Must start with `alias/`, 1-256 alphanumeric chars.

## Key Policy Operations
```bash
aws kms get-key-policy --key-id {{u.key_id}} --policy-name default
aws kms put-key-policy --key-id {{u.key_id}} --policy-name default --policy '{{u.policy}}'
```

## Grant Operations
```bash
aws kms create-grant --key-id {{u.key_id}} --grantee-principal {{u.grantee}} --operations Encrypt Decrypt
aws kms list-grants --key-id {{u.key_id}}
aws kms retire-grant --key-id {{u.key_id}} --grant-id {{u.grant_id}}
aws kms revoke-grant --key-id {{u.key_id}} --grant-id {{u.grant_id}}
```

## Encrypt/Decrypt
```bash
aws kms encrypt --key-id {{u.key_id}} --plaintext "{{u.plaintext}}" --encryption-context key=value
aws kms decrypt --ciphertext-blob {{u.ciphertext}} --encryption-context key=value
aws kms re-encrypt --ciphertext-blob {{u.ciphertext}} --destination-key-id {{u.new_key_id}}
```
Plaintext: Max 4096 bytes. For larger data, use envelope encryption.

## Data Key Operations
```bash
aws kms generate-data-key --key-id {{u.key_id}} --key-spec AES_256
aws kms generate-data-key-without-plaintext --key-id {{u.key_id}} --key-spec AES_256
aws kms generate-random --number-of-bytes {{u.bytes}}
```
Envelope encryption pattern: Gen data key → encrypt locally → store ciphertext + encrypted key → decrypt with KMS.

## Multi-Region Key Operations
```bash
aws kms replicate-key --key-id {{u.key_id}} --replica-region {{u.region}} --policy '{{u.policy}}'
aws kms update-primary-region --key-id {{u.key_id}} --primary-region {{u.new_primary_region}}
```

## Key States

| State | Operations Allowed |
|-------|-------------------|
| Enabled | All |
| Disabled | DescribeKey, EnableKey, ScheduleKeyDeletion |
| PendingDeletion | CancelKeyDeletion, DescribeKey |
| PendingImport | ImportKeyMaterial, DescribeKey |
| Unavailable | DescribeKey only |