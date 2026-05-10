# Secrets Manager Troubleshooting

Common Secrets Manager error codes, recovery procedures.

## Error Code Reference

### ResourceNotFoundException
```
Error: Secret not found: {{secret_id}}
```
**Cause**: Secret deleted or wrong ID.
**Resolution**:
```bash
# List secrets
aws secretsmanager list-secrets --output json
```

### InvalidRequestException
```
Error: Invalid request
```
**Cause**: Missing required parameters.
**Resolution**: Check required fields (Name, SecretString).

### DecryptionFailure
```
Error: Unable to decrypt secret
```
**Cause**: KMS key unavailable or no decrypt permission.
**Resolution**:
```bash
# Check KMS key
aws kms describe-key --key-id {{kms_key_id}}

# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{{account}}:user/{{user}} \
  --action-names kms:Decrypt \
  --resource-arns arn:aws:kms:{{region}}:{{account}}:key/{{key_id}}
```

## Recovery Procedures

### Secret Deleted
```bash
# Check if in recovery window
aws secretsmanager describe-secret --secret-id {{secret_id}}

# Restore if within window
aws secretsmanager restore-secret --secret-id {{secret_id}}
```

### Rotation Failed
```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/{{rotation_function}} --follow

# Cancel rotation
aws secretsmanager cancel-rotate-secret --secret-id {{secret_id}}
```