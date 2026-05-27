# AWS CLI Usage - DynamoDB

AWS CLI commands for DynamoDB operations. All commands use `--region {{r.region}} --output json`.

## Common JSON Paths (Centralized)

```
# Create Table:      .TableDescription.{TableName,TableStatus,TableArn}
# Describe Table:    .Table.{TableStatus,KeySchema,ItemCount,TableSizeBytes,BillingModeSummary,BillingMode}
# List Tables:       .TableNames[]
# Update Table:      .TableDescription.TableStatus
# Delete Table:      .TableDescription.TableStatus ("DELETING")
# Get Item:          .Item
# Put Item:          Empty (or .Attributes)
# Query/Scan:        .{Items[],Count,ScannedCount,LastEvaluatedKey}
# Create Backup:     .BackupDetails.{BackupStatus,BackupArn}
# Create GSI:        .TableDescription.GlobalSecondaryIndexes
# Enable TTL:        .TimeToLiveSpecification.{AttributeName,Enabled}
```

## Table Operations

### Create Table
```bash
# Provisioned
aws dynamodb create-table \
  --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.PartitionKey}},AttributeType=S AttributeName={{user.SortKey}},AttributeType=N \
  --key-schema AttributeName={{user.PartitionKey}},KeyType=HASH AttributeName={{user.SortKey}},KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --sse-specification Enabled=true,SSEType=KMS

# On-demand
aws dynamodb create-table --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.PartitionKey}},AttributeType=S \
  --key-schema AttributeName={{user.PartitionKey}},KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```
AttributeType: `S`(String), `N`(Number), `B`(Binary).

### Describe / List / Update / Delete
```bash
aws dynamodb describe-table --table-name {{user.TableName}}
aws dynamodb list-tables
aws dynamodb update-table --table-name {{user.TableName}} \
  --provisioned-throughput ReadCapacityUnits={{user.NewRCU}},WriteCapacityUnits={{user.NewWCU}}
aws dynamodb update-table --table-name {{user.TableName}} --billing-mode PAY_PER_REQUEST
aws dynamodb delete-table --table-name {{user.TableName}}

# Waiters
aws dynamodb wait table-exists --table-name {{user.TableName}}
aws dynamodb wait table-not-exists --table-name {{user.TableName}}
```

## Item Operations

### Put / Get / Update / Delete Item
```bash
# Put
aws dynamodb put-item --table-name {{user.TableName}} \
  --item '{"id":{"S":"user123"},"name":{"S":"John"},"age":{"N":"30"}}'
# Conditional put
aws dynamodb put-item --table-name {{user.TableName}} \
  --item '{"id":{"S":"user123"}}' --condition-expression "attribute_not_exists(id)"

# Get
aws dynamodb get-item --table-name {{user.TableName}} \
  --key '{"id":{"S":"user123"}}' --consistent-read

# Update
aws dynamodb update-item --table-name {{user.TableName}} \
  --key '{"id":{"S":"user123"}}' \
  --update-expression "SET #n = :name" \
  --expression-attribute-names '{"#n":"name"}' \
  --expression-attribute-values '{":name":{"S":"Jane"}}' \
  --return-values ALL_NEW

# Delete
aws dynamodb delete-item --table-name {{user.TableName}} \
  --key '{"id":{"S":"user123"}}' --return-values ALL_OLD
```
ReturnValues: `NONE`, `ALL_OLD`, `UPDATED_OLD`, `ALL_NEW`, `UPDATED_NEW`.

### Query / Scan
```bash
aws dynamodb query --table-name {{user.TableName}} \
  --key-condition-expression "id = :id AND created_at >= :date" \
  --expression-attribute-values '{":id":{"S":"user123"},":date":{"S":"2024-01-01"}}' \
  --limit 100

aws dynamodb scan --table-name {{user.TableName}} \
  --filter-expression "age > :min_age" \
  --expression-attribute-values '{":min_age":{"N":"25"}}' --limit 100

# Parallel scan (large tables)
aws dynamodb scan --table-name {{user.TableName}} --total-segments 4 --segment 0
```

## Global Secondary Index (GSI)

```bash
# Create GSI
aws dynamodb update-table --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.GSIKey}},AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"{{user.GSIName}}","KeySchema":[{"AttributeName":"{{user.GSIKey}}","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}}}]'

# Describe / Delete GSI
aws dynamodb describe-table --table-name {{user.TableName}} --query "Table.GlobalSecondaryIndexes[?IndexName=='{{user.GSIName}}']"
aws dynamodb update-table --table-name {{user.TableName}} \
  --global-secondary-index-updates '[{"Delete":{"IndexName":"{{user.GSIName}}"}}]'
```
ProjectionType: `ALL`, `KEYS_ONLY`, `INCLUDE`.

## Backup & Restore

```bash
aws dynamodb create-backup --table-name {{user.TableName}} --backup-name {{user.BackupName}}
aws dynamodb list-backups --table-name {{user.TableName}}
aws dynamodb restore-table-from-backup --target-table-name {{user.NewTableName}} --backup-arn {{user.BackupArn}}
aws dynamodb restore-table-to-point-in-time --source-table-name {{user.SourceTable}} \
  --target-table-name {{user.NewTableName}} --restore-date-time "2024-01-15T12:00:00Z"
```

## TTL & Streams

```bash
aws dynamodb update-time-to-live --table-name {{user.TableName}} \
  --time-to-live-specification AttributeName={{user.TTLAttribute}},Enabled=true
aws dynamodb describe-time-to-live --table-name {{user.TableName}}
aws dynamodb update-table --table-name {{user.TableName}} \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```
StreamViewType: `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE`, `NEW_AND_OLD_IMAGES`.