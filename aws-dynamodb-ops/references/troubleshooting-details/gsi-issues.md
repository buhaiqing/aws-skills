# DynamoDB GSI Issues — Detailed Recovery

## GSI Backlogged

```bash
aws dynamodb describe-table --table-name {{table_name}} \
  --query "Table.GlobalSecondaryIndexes[?IndexName=='{{index_name}}']"
# If IndexStatus is CREATING, wait
aws dynamodb wait table-exists --table-name {{table_name}}
```

## GSI Projection Too Small

Must delete and recreate:

```bash
aws dynamodb update-table --table-name {{table_name}} \
  --global-secondary-index-updates '[{"Delete": {"IndexName": "{{index_name}}"}}]'
# Wait for deletion, then recreate with ALL projection
aws dynamodb update-table --table-name {{table_name}} \
  --attribute-definitions ... \
  --global-secondary-index-updates '[{"Create": {"IndexName": "{{index_name}}", "Projection": {"ProjectionType": "ALL"}, ...}}]'
```