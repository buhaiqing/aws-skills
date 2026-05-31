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

## CloudWatch/CloudTrail Integration

### Monitor API Throttling
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/KMS \
  --metric-name ThrottledRequests \
  --dimensions Name=KeyId,Value={{u.key_id}} \
  --statistics Sum --period 3600 \
  --start-time $(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z) \
  --end-time $(date -u +%Y-%m-%dT00:00:00Z) \
  --region {{u.region}}
```

### Audit Security Events
```bash
# Monitor key disable events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=DisableKey \
  --start-time $(date -d '-24 hours' -u +%Y-%m-%dT%H:%M:%SZ)

# Monitor key deletion scheduling
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ScheduleKeyDeletion \
  --start-time $(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z)

# Monitor policy changes
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutKeyPolicy \
  --start-time $(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z)
```

### Find Unused Keys
```bash
# Keys with no Decrypt operations in 90 days
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  usage=$(aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceName,AttributeValue=$key_id \
    --start-time $(date -d '-90 days' -u +%Y-%m-%dT00:00:00Z) \
    --query "Events[?EventName=='Decrypt']" --output text)
  [ -z "$usage" ] && echo "UNUSED: $key_id"
done
```

### Compliance Scan Scripts
```bash
# Rotation compliance scan
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  rotation=$(aws kms get-key-rotation-status --key-id $key_id --query "KeyRotationEnabled" --output text)
  spec=$(aws kms describe-key --key-id $key_id --query "KeyMetadata.KeySpec" --output text)
  [ "$rotation" = "False" ] && [ "$spec" = "SYMMETRIC_DEFAULT" ] && echo "NON_COMPLIANT: $key_id"
done

# Key state audit
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  state=$(aws kms describe-key --key-id $key_id --query "KeyMetadata.KeyState" --output text)
  [ "$state" != "Enabled" ] && echo "ALERT: $key_id state=$state"
done
```

## P3 Maintenance Scripts

### Find Keys Missing Environment Tags
```bash
#!/bin/bash
echo "=== Keys Missing Environment Tag ==="
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  env_tag=$(aws kms list-resource-tags --key-id "$key_id" \
    --query "Tags[?TagKey=='Environment'].TagValue" --output text)
  if [ -z "$env_tag" ]; then
    alias=$(aws kms list-aliases --key-id "$key_id" \
      --query "Aliases[0].AliasName" --output text)
    echo "MISSING_ENV_TAG: $key_id (alias: $alias)"
  fi
done
```

### Find Orphaned Aliases
```bash
#!/bin/bash
echo "=== Orphaned Aliases ==="
for alias_name in $(aws kms list-aliases --query "Aliases[].AliasName" --output text); do
  target_key=$(aws kms list-aliases \
    --query "Aliases[?AliasName=='$alias_name'].TargetKeyId" --output text)

  if [ -n "$target_key" ]; then
    # Check if target key exists
    if ! aws kms describe-key --key-id "$target_key" --query "KeyMetadata.KeyState" --output text 2>/dev/null; then
      echo "ORPHANED_ALIAS: $alias_name -> $target_key (KEY_NOT_FOUND)"
    fi
  fi
done
```

### Find Keys Without Description
```bash
#!/bin/bash
echo "=== Keys Without Description ==="
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  desc=$(aws kms describe-key --key-id "$key_id" \
    --query "KeyMetadata.Description" --output text)
  if [ -z "$desc" ]; then
    alias=$(aws kms list-aliases --key-id "$key_id" \
      --query "Aliases[0].AliasName" --output text)
    echo "NO_DESCRIPTION: $key_id (alias: $alias)"
  fi
done
```

### Audit Grant Count Per Key
```bash
#!/bin/bash
echo "=== Grant Count Audit (threshold: 400) ==="
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  grant_count=$(aws kms list-grants --key-id "$key_id" \
    --query "Grants | length" --output text)
  if [ "$grant_count" -gt 400 ]; then
    echo "HIGH_GRANT_COUNT: $key_id has $grant_count grants (limit: 500)"
  fi
done
```

### Quarterly Health Check Report
```bash
#!/bin/bash
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           KMS Quarterly Health Check Report                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

total_keys=0
healthy_keys=0
p0_issues=0
p2_issues=0
p3_issues=0

# Scan all keys
for key_id in $(aws kms list-keys --query "Keys[].KeyId" --output text); do
  ((total_keys++))

  # Check key state
  state=$(aws kms describe-key --key-id "$key_id" \
    --query "KeyMetadata.KeyState" --output text)

  if [ "$state" = "Disabled" ]; then
    echo "[P0] $key_id: Key disabled"
    ((p0_issues++))
    continue
  elif [ "$state" = "PendingDeletion" ]; then
    echo "[P0] $key_id: Key pending deletion"
    ((p0_issues++))
    continue
  fi

  # Check rotation for symmetric keys
  spec=$(aws kms describe-key --key-id "$key_id" \
    --query "KeyMetadata.KeySpec" --output text)

  if [ "$spec" = "SYMMETRIC_DEFAULT" ]; then
    rotation=$(aws kms get-key-rotation-status --key-id "$key_id" \
      --query "KeyRotationEnabled" --output text)
    if [ "$rotation" = "False" ]; then
      echo "[P2] $key_id: Rotation not enabled"
      ((p2_issues++))
    fi
  fi

  # Check tags
  env_tag=$(aws kms list-resource-tags --key-id "$key_id" \
    --query "Tags[?TagKey=='Environment']" --output text)
  if [ -z "$env_tag" ]; then
    echo "[P3] $key_id: Missing Environment tag"
    ((p3_issues++))
  fi

  # Count healthy
  ((healthy_keys++))
done

# Calculate compliance score
if [ "$total_keys" -gt 0 ]; then
  score=$((healthy_keys * 100 / total_keys))
else
  score=0
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║ Summary                                                           ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
printf "║ %-64s ║\n" "Total Keys: $total_keys"
printf "║ %-64s ║\n" "Healthy: $healthy_keys"
printf "║ %-64s ║\n" "P0 Issues: $p0_issues (Critical)"
printf "║ %-64s ║\n" "P2 Issues: $p2_issues (Important)"
printf "║ %-64s ║\n" "P3 Issues: $p3_issues (Maintenance)"
printf "║ %-64s ║\n" "Compliance Score: $score/100"
echo "╚══════════════════════════════════════════════════════════════════╝"
```