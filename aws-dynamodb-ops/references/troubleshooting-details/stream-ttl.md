# DynamoDB Stream / TTL / Backup Issues — Detailed Recovery

## Stream Not Triggering Lambda

Causes: Lambda role permissions, stream enabled but no records, timeout/memory too low.

```bash
aws dynamodb describe-table --table-name {{table_name}} --query "Table.StreamSpecification"
aws lambda list-event-source-mappings --function-name {{lambda_function}}
aws logs tail /aws/lambda/{{lambda_function}} --follow
```

## TTL Not Deleting Items

Causes: TTL not enabled, wrong attribute format (must be Number with epoch seconds).

```bash
aws dynamodb describe-time-to-live --table-name {{table_name}}
date -d "@1705000000"  # Should be future date for active TTL
```

## Backup/Restore

```bash
aws dynamodb describe-backup --backup-arn {{backup_arn}}
aws dynamodb update-continuous-backups --table-name {{table_name}} \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```