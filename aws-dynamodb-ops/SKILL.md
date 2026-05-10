# AWS DynamoDB Ops Skill

AWS DynamoDB NoSQL database operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests DynamoDB table creation, modification, or deletion
- User asks about DynamoDB items, queries, or scans
- User needs to configure Global Secondary Index (GSI) or Local Secondary Index (LSI)
- User mentions "DynamoDB", "NoSQL database", "key-value store", "DAX"
- User needs backup/restore or point-in-time recovery operations
- User asks about provisioned capacity (RCU/WCU) or on-demand mode

**SHOULD-NOT activate when:**
- RDS relational database operations (use `aws-rds-ops`)
- ElastiCache Redis/Memcached operations (use `aws-elasticache-ops`)
- DocumentDB operations
- MongoDB operations (use Amazon DocumentDB skill)
- Neptune graph database operations

**Delegation:**
- Lambda triggers → `aws-lambda-ops` (Lambda-DynamoDB integration)
- CloudWatch alarms → `aws-cloudwatch-ops` (monitoring setup)
- IAM roles → `aws-iam-ops` (role creation for DynamoDB access)
- KMS keys → `aws-kms-ops` (encryption key setup)
- S3 export/import → `aws-s3-ops` (data export to S3)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Table | Yes | None |
| Describe Table | Yes | None |
| List Tables | Yes | None |
| Update Table | Yes | Capacity/index changes |
| Delete Table | Yes | **Human confirmation** |
| Put Item | Yes | None |
| Get Item | Yes | None |
| Update Item | Yes | Conditional writes |
| Delete Item | Yes | Human confirmation (optional) |
| Query | Yes | None |
| Scan | Yes | Pagination required |
| Create GSI | Yes | None |
| Delete GSI | Yes | Human confirmation |
| Create Backup | Yes | None |
| Restore Backup | Yes | None |
| Enable TTL | Yes | None |
| Enable Streams | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.TableName}}` | User input | my-table-prod |
| `{{user.PrimaryKey}}` | User input | partition-key |
| `{{user.SortKey}}` | User input | sort-key (optional) |
| `{{user.RCU}}` | User input | 5 (Read Capacity Units) |
| `{{user.WCU}}` | User input | 5 (Write Capacity Units) |

**Never commit real credentials. Always use `{{env.*}}` or `{{user.*}}` placeholders.**

## Execution Flow

### Pre-flight
```
1. Check AWS CLI availability: aws --version
2. Validate credentials: aws sts get-caller-identity
3. Confirm region: aws dynamodb list-tables --region {{env.AWS_DEFAULT_REGION}}
4. Check quotas: aws service-quotas get-service-quota --service-code dynamodb --quota-code L-...
5. Validate table name uniqueness: aws dynamodb describe-table --table-name {{user.TableName}}
```

### Execute (Primary: CLI)
```
aws dynamodb create-table \
  --table-name {{user.TableName}} \
  --attribute-definitions AttributeName={{user.PrimaryKey}},AttributeType=S \
  --key-schema AttributeName={{user.PrimaryKey}},KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits={{user.RCU}},WriteCapacityUnits={{user.WCU}} \
  --output json
```

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK:
```python
import boto3
dynamodb = boto3.client('dynamodb', region_name='{{env.AWS_DEFAULT_REGION}}')
response = dynamodb.create_table(
    TableName='{{user.TableName}}',
    AttributeDefinitions=[{'AttributeName': '{{user.PrimaryKey}}', 'AttributeType': 'S'}],
    KeySchema=[{'AttributeName': '{{user.PrimaryKey}}', 'KeyType': 'HASH'}],
    ProvisionedThroughput={'ReadCapacityUnits': {{user.RCU}}, 'WriteCapacityUnits': {{user.WCU}}
)
```

### Validate
```
1. Poll status: aws dynamodb describe-table --table-name {{user.TableName}}
2. Wait for terminal state: ACTIVE (create), DELETING (delete)
3. Max wait: 10 minutes for create, 5 minutes for delete
4. Validate key schema and indexes
```

### Recover
| Error Type | Action |
|------------|---------|
| TableAlreadyExists | HALT - provide existing table info |
| LimitExceededException | HALT - wait or reduce capacity |
| ProvisionedThroughputExceededException | Backoff, retry with exponential backoff |
| ResourceNotFoundException | HALT - table does not exist |
| ConditionalCheckFailedException | HALT - item condition failed |
| ValidationException | Fix args; retry once |
| Throttling (429) | Exponential backoff; max 3 retries |
| 5xx Internal | Retry 3x; then HALT |

## Safety Gates

### Table Deletion (Critical)
```
BEFORE delete-table:
1. Display: "Deleting {{user.TableName}} will permanently remove all data and indexes"
2. Ask: "Confirm dependencies - no Lambda triggers, no Streams consumers?"
3. Ask: "Type 'DELETE {{user.TableName}}' to confirm"
4. Human must type exact confirmation string
5. Proceed only after confirmation matches
```

### GSI Deletion
```
BEFORE delete-gsi:
1. Display: "GSI {{user.IndexName}} will be permanently deleted"
2. Ask: "Type 'DELETE GSI {{user.IndexName}}' to confirm"
3. Proceed only after confirmation matches
```

## Output Convention

Always use `--output json` for agent parsing.

Key JSON paths:
- `.Table.TableStatus` - table state (ACTIVE, CREATING, DELETING)
- `.Table.TableName` - table name
- `.Table.KeySchema` - primary key structure
- `.Table.GlobalSecondaryIndexes` - GSI list
- `.Table.ProvisionedThroughput.ReadCapacityUnits` - RCU
- `.Table.ProvisionedThroughput.WriteCapacityUnits` - WCU
- `.Table.ItemCount` - approximate item count
- `.Item` - item attributes

## Related Skills

- `aws-lambda-ops` - Lambda triggers for DynamoDB Streams
- `aws-eks-ops` - Kubernetes applications using DynamoDB
- `aws-cloudwatch-ops` - DynamoDB metrics and alarms
- `aws-iam-ops` - IAM roles for DynamoDB access
- `aws-kms-ops` - Encryption key management
- `aws-s3-ops` - Export/import DynamoDB data

## Reference Files

- `references/aws-cli-usage.md` - CLI command reference
- `references/boto3-sdk-usage.md` - Python SDK patterns
- `references/core-concepts.md` - DynamoDB architecture, capacity modes
- `references/troubleshooting.md` - Error codes, recovery procedures
- `assets/example-config.yaml` - Configuration examples