# AWS CLI Usage - DynamoDB

AWS CLI commands for DynamoDB operations. All commands use `--output json`.

## Table Operations

### Create Table (Provisioned Capacity)
```bash
aws dynamodb create-table \
  --table-name {{user.TableName}} \
  --attribute-definitions \
    AttributeName={{user.PartitionKey}},AttributeType=S \
    AttributeName={{user.SortKey}},AttributeType=N \
  --key-schema \
    AttributeName={{user.PartitionKey}},KeyType=HASH \
    AttributeName={{user.SortKey}},KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId={{user.KmsKeyId}} \
  --tags Key=Environment,Value=production \
  --output json
```

**AttributeType values:**
- `S` - String
- `N` - Number
- `B` - Binary

**JSON paths:**
- `.Table.TableName`
- `.Table.TableStatus` → "CREATING" → "ACTIVE"
- `.Table.TableArn`

### Create Table (On-Demand)
```bash
aws dynamodb create-table \
  --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.PartitionKey}},AttributeType=S \
  --key-schema AttributeName={{user.PartitionKey}},KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --output json
```

### Describe Table
```bash
aws dynamodb describe-table \
  --table-name {{user.TableName}} \
  --output json
```

**JSON paths:**
- `.Table.TableStatus` → "ACTIVE", "CREATING", "DELETING", "UPDATING"
- `.Table.KeySchema[].AttributeName` → partition/sort key names
- `.Table.KeySchema[].KeyType` → "HASH" (partition), "RANGE" (sort)
- `.Table.AttributeDefinitions[].AttributeType` → S/N/B
- `.Table.GlobalSecondaryIndexes` → GSI list
- `.Table.LocalSecondaryIndexes` → LSI list
- `.Table.ProvisionedThroughput.ReadCapacityUnits` → RCU
- `.Table.ProvisionedThroughput.WriteCapacityUnits` → WCU
- `.Table.BillingModeSummary.BillingMode` → "PROVISIONED" or "PAY_PER_REQUEST"
- `.Table.ItemCount` → approximate count
- `.Table.TableSizeBytes` → size in bytes
- `.Table.StreamSpecification.StreamEnabled` → boolean
- `.Table.SSEDescription.Status` → encryption status

### List Tables
```bash
aws dynamodb list-tables --output json
```

**JSON paths:**
- `.TableNames[]` → list of table names

### Update Table (Capacity)
```bash
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --provisioned-throughput ReadCapacityUnits={{user.NewRCU}},WriteCapacityUnits={{user.NewWCU}} \
  --output json
```

### Update Table (Billing Mode)
```bash
# Switch to on-demand
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --billing-mode PAY_PER_REQUEST \
  --output json

# Switch to provisioned
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --output json
```

### Delete Table
```bash
aws dynamodb delete-table \
  --table-name {{user.TableName}} \
  --output json
```

**Safety Gate:** Human confirmation required before deletion.

**JSON paths:**
- `.TableDescription.TableStatus` → "DELETING"

## Item Operations

### Put Item
```bash
aws dynamodb put-item \
  --table-name {{user.TableName}} \
  --item '{"id": {"S": "user123"}, "name": {"S": "John"}, "age": {"N": "30"}}' \
  --output json
```

**Conditional Put (prevent overwrite):**
```bash
aws dynamodb put-item \
  --table-name {{user.TableName}} \
  --item '{"id": {"S": "user123"}, "name": {"S": "John"}}' \
  --condition-expression "attribute_not_exists(id)" \
  --output json
```

### Get Item
```bash
aws dynamodb get-item \
  --table-name {{user.TableName}} \
  --key '{"id": {"S": "user123"}}' \
  --consistent-read \
  --output json
```

**JSON paths:**
- `.Item.{attribute}.S` → string value
- `.Item.{attribute}.N` → number value
- `.Item.{attribute}.B` → binary value

### Update Item
```bash
aws dynamodb update-item \
  --table-name {{user.TableName}} \
  --key '{"id": {"S": "user123"}}' \
  --update-expression "SET #n = :name, age = :age ADD version :inc" \
  --expression-attribute-names '{"#n": "name"}' \
  --expression-attribute-values '{":name": {"S": "Jane"}, ":age": {"N": "35"}, ":inc": {"N": "1"}}' \
  --return-values ALL_NEW \
  --output json
```

**ReturnValues options:**
- `NONE` - default
- `ALL_OLD` - return old item
- `UPDATED_OLD` - return old updated attributes
- `ALL_NEW` - return new item
- `UPDATED_NEW` - return new updated attributes

### Delete Item
```bash
aws dynamodb delete-item \
  --table-name {{user.TableName}} \
  --key '{"id": {"S": "user123"}}' \
  --return-values ALL_OLD \
  --output json
```

### Query
```bash
aws dynamodb query \
  --table-name {{user.TableName}} \
  --key-condition-expression "id = :id AND created_at >= :date" \
  --expression-attribute-values '{":id": {"S": "user123"}, ":date": {"S": "2024-01-01"}}' \
  --consistent-read \
  --limit 100 \
  --output json
```

**JSON paths:**
- `.Items[]` → matching items
- `.Count` → number of items returned
- `.ScannedCount` → items scanned (for filtering)
- `.LastEvaluatedKey` → pagination key

**Pagination:**
```bash
aws dynamodb query \
  --table-name {{user.TableName}} \
  --key-condition-expression "id = :id" \
  --expression-attribute-values '{":id": {"S": "user123"}}' \
  --exclusive-start-key '{"id": {"S": "user123"}, "created_at": {"S": "2024-01-15"}}' \
  --output json
```

### Scan
```bash
aws dynamodb scan \
  --table-name {{user.TableName}} \
  --filter-expression "age > :min_age" \
  --expression-attribute-values '{":min_age": {"N": "25"}}' \
  --limit 100 \
  --output json
```

**Parallel Scan (for large tables):**
```bash
aws dynamodb scan \
  --table-name {{user.TableName}} \
  --total-segments 4 \
  --segment 0 \
  --output json
```

## Global Secondary Index (GSI) Operations

### Create GSI
```bash
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.GSIKey}},AttributeType=S \
  --global-secondary-index-updates '[{"Create": {"IndexName": "{{user.GSIName}}", "KeySchema": [{"AttributeName": "{{user.GSIKey}}", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}, "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}}}]' \
  --output json
```

**ProjectionType options:**
- `ALL` - all attributes
- `KEYS_ONLY` - only key attributes
- `INCLUDE` - specified attributes

### Describe GSI
```bash
aws dynamodb describe-table \
  --table-name {{user.TableName}} \
  --query "Table.GlobalSecondaryIndexes[?IndexName=='{{user.GSIName}}']" \
  --output json
```

**JSON paths:**
- `.IndexStatus` → "CREATING", "ACTIVE", "DELETING", "UPDATING"
- `.KeySchema[]` → index key structure
- `.Projection.ProjectionType` → projection type
- `.ProvisionedThroughput` → capacity

### Delete GSI
```bash
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --global-secondary-index-updates '[{"Delete": {"IndexName": "{{user.GSIName}}}}]' \
  --output json
```

## Local Secondary Index (LSI) Operations

### Create LSI (at table creation)
```bash
aws dynamodb create-table \
  --table-name {{user.TableName}} \
  --attribute-definitions \
    AttributeName={{user.PartitionKey}},AttributeType=S \
    AttributeName={{user.SortKey}},AttributeType=S \
    AttributeName={{user.LSIKey}},AttributeType=N \
  --key-schema \
    AttributeName={{user.PartitionKey}},KeyType=HASH \
    AttributeName={{user.SortKey}},KeyType=RANGE \
  --local-secondary-indexes '[{"IndexName": "{{user.LSIName}}", "KeySchema": [{"AttributeName": "{{user.PartitionKey}}", "KeyType": "HASH"}, {"AttributeName": "{{user.LSIKey}}", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}}]'' \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --output json
```

## Backup Operations

### Create Backup
```bash
aws dynamodb create-backup \
  --table-name {{user.TableName}} \
  --backup-name {{user.BackupName}} \
  --output json
```

**JSON paths:**
- `.BackupDetails.BackupStatus` → "CREATING", "AVAILABLE", "DELETED"
- `.BackupDetails.BackupArn`

### List Backups
```bash
aws dynamodb list-backups \
  --table-name {{user.TableName}} \
  --output json
```

### Restore Backup
```bash
aws dynamodb restore-table-from-backup \
  --target-table-name {{user.NewTableName}} \
  --backup-arn {{user.BackupArn}} \
  --output json
```

### Restore to Point-in-Time
```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name {{user.SourceTable}} \
  --target-table-name {{user.NewTableName}} \
  --restore-date-time "2024-01-15T12:00:00Z" \
  --output json
```

## TTL Operations

### Enable TTL
```bash
aws dynamodb update-time-to-live \
  --table-name {{user.TableName}} \
  --time-to-live-specification AttributeName={{user.TTLAttribute}},Enabled=true \
  --output json
```

### Describe TTL
```bash
aws dynamodb describe-time-to-live \
  --table-name {{user.TableName}} \
  --output json
```

**JSON paths:**
- `.TimeToLiveSpecification.AttributeName` → TTL attribute name
- `.TimeToLiveSpecification.Enabled` → boolean

## Stream Operations

### Enable Stream
```bash
aws dynamodb update-table \
  --table-name {{user.TableName}} \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --output json
```

**StreamViewType options:**
- `KEYS_ONLY` - only key attributes
- `NEW_IMAGE` - new item after modification
- `OLD_IMAGE` - old item before modification
- `NEW_AND_OLD_IMAGES` - both old and new

### Describe Stream
```bash
aws dynamodb describe-stream \
  --stream-arn {{user.StreamArn}} \
  --output json
```

## Wait Operations

```bash
# Wait for table exists (active)
aws dynamodb wait table-exists --table-name {{user.TableName}}

# Wait for table not-exists (deleted)
aws dynamodb wait table-not-exists --table-name {{user.TableName}}
```

## Capacity Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `PROVISIONED` | RCU/WCU specified | Predictable workload, cost control |
| `PAY_PER_REQUEST` | On-demand, auto-scaling | Unpredictable workload, no capacity planning |

## Common Options

```bash
--consistent-read                    # Strong consistency read (default: eventual)
--return-consumed-capacity TOTAL     # Show capacity consumed
--return-values ALL_NEW              # Return updated item
--condition-expression               # Conditional write
--projection-expression              # Select specific attributes
--filter-expression                  # Filter scan/query results
--limit 100                          # Pagination limit
--select ALL_ATTRIBUTES              # Return all attributes (scan)
```