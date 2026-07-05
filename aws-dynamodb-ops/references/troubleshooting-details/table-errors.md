# DynamoDB Table Errors — Detailed Recovery

## TableAlreadyExists

```bash
aws dynamodb describe-table --table-name {{table_name}}
aws dynamodb create-table --table-name {{new_table_name}} ...
```

## ResourceNotFoundException

```bash
aws dynamodb list-tables
aws dynamodb describe-table --table-name {{table_name}} --region {{region}}
```