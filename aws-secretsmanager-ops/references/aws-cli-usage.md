# AWS CLI Usage - Secrets Manager

AWS CLI commands for Secrets Manager operations. All commands use `--output json`.

## Secret Operations

### Create Secret
```bash
aws secretsmanager create-secret \
  --name {{user.SecretName}} \
  --description "{{user.Description}}" \
  --secret-string '{{user.SecretString}}' \
  --kms-key-id {{user.KmsKeyId}} \
  --tags Key=Environment,Value=production \
  --output json
```

### Get Secret Value
```bash
aws secretsmanager get-secret-value \
  --secret-id {{user.SecretId}} \
  --version-id {{user.VersionId}} \
  --version-stage {{user.VersionStage}} \
  --output json
```

### Update Secret
```bash
aws secretsmanager put-secret-value \
  --secret-id {{user.SecretId}} \
  --secret-string '{{user.NewSecretString}}' \
  --version-stages AWSCURRENT \
  --output json
```

### Delete Secret
```bash
# Soft delete (recovery window)
aws secretsmanager delete-secret \
  --secret-id {{user.SecretId}} \
  --recovery-window-in-days 30 \
  --output json

# Immediate delete (no recovery)
aws secretsmanager delete-secret \
  --secret-id {{user.SecretId}} \
  --force-delete-without-recovery \
  --output json
```

### Restore Secret
```bash
aws secretsmanager restore-secret \
  --secret-id {{user.SecretId}} \
  --output json
```

## Rotation Operations

### Rotate Secret
```bash
aws secretsmanager rotate-secret \
  --secret-id {{user.SecretId}} \
  --rotation-lambda-arn {{user.LambdaArn}} \
  --rotation-rules AutomaticallyAfterDays=30 \
  --output json
```

### Cancel Rotation
```bash
aws secretsmanager cancel-rotate-secret \
  --secret-id {{user.SecretId}} \
  --output json
```

## Replication Operations

### Replicate Secret
```bash
aws secretsmanager replicate-secret-to-regions \
  --secret-id {{user.SecretId}} \
  --add-replica-regions Region={{user.TargetRegion}} \
  --output json
```

## Common Options

```bash
--secret-id {{user.SecretId}}           # Secret name or ARN
--secret-string '{{user.Value}}'        # Plain text secret
--secret-binary fileb://{{file}}        # Binary secret
--kms-key-id {{user.KmsKeyId}}          # KMS encryption key
--description "{{user.Description}}"    # Secret description
--recovery-window-in-days 7             # Recovery period
```