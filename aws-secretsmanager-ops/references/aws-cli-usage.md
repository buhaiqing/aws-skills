# AWS CLI Usage - Secrets Manager

AWS CLI commands for Secrets Manager operations. All commands use `--region {{r.region}} --output json`.

## Common JSON Paths (Centralized)

```
# Create Secret:     .{ARN,Name,VersionId}
# Get Secret Value:  .{ARN,Name,SecretString,SecretBinary,VersionId,CreatedDate}
# Put Secret Value:  .{ARN,Name,VersionId}
# Delete Secret:     .{ARN,Name,DeletionDate}
# Restore Secret:    .{ARN,Name}
# Rotate Secret:     .{ARN,Name,VersionId}
# Cancel Rotation:   .{ARN,Name}
# Replicate Secret:  .{ARN,Name,ReplicationStatus}
```

## Secret Operations

### Create Secret
```bash
aws secretsmanager create-secret \
  --name {{user.SecretName}} \
  --description "{{user.Description}}" \
  --secret-string '{{user.SecretString}}' \
  --kms-key-id {{user.KmsKeyId}} \
  --tags Key=Environment,Value=production
```

### Get Secret Value
```bash
aws secretsmanager get-secret-value --secret-id {{user.SecretId}}
aws secretsmanager get-secret-value --secret-id {{user.SecretId}} --version-id {{user.VersionId}}
```

### Update Secret
```bash
aws secretsmanager put-secret-value \
  --secret-id {{user.SecretId}} \
  --secret-string '{{user.NewSecretString}}' \
  --version-stages AWSCURRENT
```

### Delete / Restore Secret
```bash
# Soft delete (default 30-day recovery window)
aws secretsmanager delete-secret --secret-id {{user.SecretId}} --recovery-window-in-days 30

# Immediate delete (no recovery)
aws secretsmanager delete-secret --secret-id {{user.SecretId}} --force-delete-without-recovery

# Restore a deleted secret (within recovery window)
aws secretsmanager restore-secret --secret-id {{user.SecretId}}
```

## Rotation Operations

```bash
aws secretsmanager rotate-secret \
  --secret-id {{user.SecretId}} \
  --rotation-lambda-arn {{user.LambdaArn}} \
  --rotation-rules AutomaticallyAfterDays=30

aws secretsmanager cancel-rotate-secret --secret-id {{user.SecretId}}
```

## Replication Operations

```bash
aws secretsmanager replicate-secret-to-regions \
  --secret-id {{user.SecretId}} \
  --add-replica-regions Region={{user.TargetRegion}}
```

## Common Options

```
--secret-id {{user.SecretId}}            # Secret name or ARN
--secret-string '{{user.Value}}'         # Plain text secret
--secret-binary fileb://{{file}}         # Binary secret
--kms-key-id {{user.KmsKeyId}}           # KMS encryption key
--description "{{user.Description}}"     # Secret description
--recovery-window-in-days 7-30           # Recovery period
--force-delete-without-recovery          # Immediate permanent deletion
--version-stages AWSCURRENT              # Version stage label
```