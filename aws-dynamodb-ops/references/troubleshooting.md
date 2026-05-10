# DynamoDB Troubleshooting

Common DynamoDB error codes, recovery procedures, and operational troubleshooting.

## Error Code Reference

### Table Errors

#### TableAlreadyExists
```
Error: Table already exists: {{table_name}}
```
**Cause**: Attempting to create table with existing name.
**Resolution**:
```bash
# Check existing table
aws dynamodb describe-table --table-name {{table_name}}

# Use different table name for new table
aws dynamodb create-table --table-name {{new_table_name}} ...
```

#### ResourceNotFoundException
```
Error: Table not found: {{table_name}}
```
**Cause**: Table deleted, wrong name, or wrong region.
**Resolution**:
```bash
# List tables in current region
aws dynamodb list-tables

# Check specific region
aws dynamodb describe-table --table-name {{table_name}} --region {{region}}
```

#### LimitExceededException
```
Error: Too many tables or indexes for this account
```
**Cause**: Reached quota limit for tables or GSIs.
**Resolution**:
- Request quota increase via Service Quotas console
- Delete unused tables/indexes
- Consolidate tables using single-table design

### Capacity/Throughput Errors

#### ProvisionedThroughputExceededException
```
Error: The level of configured provisioned throughput for the table was exceeded
```
**Cause**: Request rate exceeds provisioned capacity.

**Resolution Options:**
1. **Immediate - Exponential backoff:**
```python
import time
import random

def retry_with_backoff(operation, max_retries=10):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                delay = min(2 ** attempt * 0.1 + random.uniform(0, 0.1), 60)
                time.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

2. **Short-term - Enable auto-scaling:**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/{{table_name}} \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity {{user.RCU}} \
  --max-capacity {{user.MaxRCU}}
```

3. **Long-term - Switch to on-demand:**
```bash
aws dynamodb update-table \
  --table-name {{table_name}} \
  --billing-mode PAY_PER_REQUEST
```

### Conditional Check Errors

#### ConditionalCheckFailedException
```
Error: The conditional request failed
```
**Cause**: Condition expression evaluated to false.

**Common Scenarios:**
- `attribute_not_exists(id)` - Item already exists
- `attribute_exists(id)` - Item doesn't exist
- Custom condition not met

**Resolution**:
```python
# Check item before conditional write
try:
    response = dynamodb.get_item(
        TableName=table_name,
        Key={'id': {'S': item_id}}
    )
    if 'Item' in response:
        # Item exists, condition will fail
        handle_existing_item()
    else:
        # Safe to put with condition
        put_with_condition()
except ClientError:
    handle_error()
```

### Validation Errors

#### ValidationException
```
Error: One or more parameter values are invalid
```
**Common Causes:**

| Error | Cause | Fix |
|-------|-------|-----|
| Attribute type mismatch | Providing wrong type | Use correct DynamoDB format: `{"S": "value"}` |
| Missing key attribute | Put/Get without full key | Include partition + sort key |
| Invalid expression syntax | Malformed condition/update expr | Check expression syntax |
| Number exceeds precision | Large numbers | Use string for large numbers |
| Empty string not allowed | Empty string value | Remove attribute or use placeholder |

**Resolution**:
```bash
# Check item format
aws dynamodb get-item --table-name {{table_name}} \
  --key '{"id": {"S": "{{id}}"}}' \
  --output json

# Verify expression syntax
aws dynamodb update-item --table-name {{table_name}} \
  --key '{"id": {"S": "{{id}}"}}' \
  --update-expression "SET #n = :v" \
  --expression-attribute-names '{"#n": "name"}' \
  --expression-attribute-values '{":v": {"S": "value"}}' \
  --output json
```

### Size Limit Errors

#### ItemCollectionSizeLimitExceededException
```
Error: Item collection size exceeded
```
**Cause**: Local Secondary Index item collection exceeds 10GB.

**Resolution**:
- Reduce item size
- Split large items
- Use Global Secondary Index instead of LSI
- Redesign partition key distribution

#### ValidationException (400KB Item)
```
Error: Item size has exceeded the maximum allowed size
```
**Cause**: Item exceeds 400KB limit.

**Resolution Options:**
1. **Compress attributes:**
```python
import gzip
import base64

compressed = base64.b64encode(gzip.compress(data.encode())).decode()
# Store compressed in Binary (B) type
```

2. **Split into multiple items:**
```python
# Item1: metadata + part1
# Item2: part2
# Item3: part3
```

3. **Store large data in S3:**
```python
# Upload to S3, store reference in DynamoDB
item = {
    'id': {'S': item_id},
    'metadata': {'S': json.dumps(metadata)},
    's3_path': {'S': f's3://bucket/{item_id}/data'}
}
```

### Transaction Errors

#### TransactionConflictException
```
Error: Transaction cancelled due to conflict
```
**Cause**: Concurrent modification of same items in transaction.

**Resolution**:
```python
# Implement retry with backoff
for attempt in range(max_retries):
    try:
        response = dynamodb.transact_write_items(
            TransactItems=transaction_items
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'TransactionConflictException':
            time.sleep(2 ** attempt)
        else:
            raise
```

#### IdempotentParameterMismatchException
```
Error: Request includes two idempotent parameters with different values
```
**Cause**: Same client token used for different transactions.

**Resolution**:
- Generate unique client token per transaction
- Or don't reuse tokens for different operations

## Throttling Handling

### Detection
```python
def check_throttling(table_name: str) -> dict:
    """Check CloudWatch metrics for throttling."""
    cloudwatch = boto3.client('cloudwatch')
    
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/DynamoDB',
        MetricName='ThrottledRequests',
        Dimensions=[
            {'Name': 'TableName', 'Value': table_name},
            {'Name': 'Operation', 'Value': 'GetItem'}
        ],
        StartTime=datetime.utcnow() - timedelta(minutes=5),
        EndTime=datetime.utcnow(),
        Period=60,
        Statistics=['Sum']
    )
    
    return response['Datapoints']
```

### Backoff Strategy
```python
class ThrottlingHandler:
    def __init__(self, max_retries: int = 10):
        self.max_retries = max_retries
    
    def execute(self, operation, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ProvisionedThroughputExceededException':
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
                else:
                    raise
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def _calculate_delay(self, attempt: int) -> float:
        # Exponential backoff with jitter
        base = min(2 ** attempt * 0.1, 60)
        jitter = random.uniform(0, base * 0.1)
        return base + jitter
```

## Hot Partition Issues

### Symptoms
- High `ProvisionedThroughputExceededException`
- Uneven CloudWatch metrics
- Specific partition keys showing high consumption

### Diagnosis
```bash
# Enable Contributor Insights
aws dynamodb update-contributor-insights \
  --table-name {{table_name}} \
  --contributor-insights-action ENABLE

# View top contributors
aws dynamodb describe-contributor-insights \
  --table-name {{table_name}}
```

### Resolution Strategies

#### 1. Write Sharding
```python
# Instead of sequential timestamps
# Use shard suffix: timestamp#0, timestamp#1, ...
def get_shard_key(timestamp: str, num_shards: int = 10) -> str:
    shard = hash(timestamp) % num_shards
    return f"{timestamp}#{shard}"
```

#### 2. Random Suffix
```python
import uuid

def distribute_writes(key: str) -> str:
    # Add random suffix to spread writes
    return f"{key}#{uuid.uuid4().hex[:4]}"
```

#### 3. Use High-Cardinality Keys
```python
# Instead of status codes
# Use composite keys with high cardinality
key = f"{user_id}#{timestamp}#{uuid.uuid4().hex}"
```

## GSI Issues

### GSI Backlogged
**Symptoms**: GSI lagging behind base table updates.

**Resolution**:
```bash
# Check GSI status
aws dynamodb describe-table --table-name {{table_name}} \
  --query "Table.GlobalSecondaryIndexes[?IndexName=='{{index_name}}']"

# If IndexStatus is CREATING, wait
aws dynamodb wait table-exists --table-name {{table_name}}
```

### GSI Projection Too Small
**Symptoms**: Frequent base table lookups when querying GSI.

**Resolution**:
```bash
# Recreate GSI with ALL projection
# Note: Must delete and recreate
aws dynamodb update-table \
  --table-name {{table_name}} \
  --global-secondary-index-updates '[{"Delete": {"IndexName": "{{index_name}}"}}]'

# Wait for deletion, then recreate
aws dynamodb update-table \
  --table-name {{table_name}} \
  --attribute-definitions ... \
  --global-secondary-index-updates '[{"Create": {"IndexName": "{{index_name}}", "Projection": {"ProjectionType": "ALL"}, ...}}]'
```

## Stream Processing Issues

### Stream Not Triggering Lambda
**Causes:**
- Lambda execution role permissions
- Stream enabled but no records
- Lambda timeout/memory too low

**Resolution**:
```bash
# Check stream status
aws dynamodb describe-table --table-name {{table_name}} \
  --query "Table.StreamSpecification"

# Verify Lambda event source mapping
aws lambda list-event-source-mappings \
  --function-name {{lambda_function}}

# Check Lambda CloudWatch logs
aws logs tail /aws/lambda/{{lambda_function}} --follow
```

## TTL Issues

### TTL Not Deleting Items
**Causes:**
- TTL not enabled on table
- Wrong attribute format (must be Number with epoch seconds)
- TTL precision (deletion within 48 hours)

**Resolution**:
```bash
# Check TTL configuration
aws dynamodb describe-time-to-live --table-name {{table_name}}

# Verify TTL attribute format
date -d "@1705000000"  # Should be future date for active TTL
```

## Backup/Restore Issues

### Backup Creation Hanging
```bash
# Check backup status
aws dynamodb describe-backup --backup-arn {{backup_arn}}

# If still CREATING, wait (large tables take time)
# Monitor with CloudWatch
```

### Point-in-Time Recovery (PITR) Not Available
**Causes:**
- PITR not enabled on table
- Trying to restore beyond 35 days
- Table deleted more than 35 days ago

**Resolution**:
```bash
# Enable PITR
aws dynamodb update-continuous-backups \
  --table-name {{table_name}} \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

## Recovery Procedures

### Table Recovery Flow
```
1. Identify error type from CloudWatch/exception
2. Check table status with describe-table
3. For throttling: implement backoff or increase capacity
4. For validation: fix input parameters
5. For size: split items or use S3
6. Max 3 retries for transient errors
7. HALT for data loss scenarios
```

### Performance Recovery
```
1. Check CloudWatch ThrottledRequests metric
2. Identify hot partitions with Contributor Insights
3. If persistent throttling:
   - Enable auto-scaling
   - Or switch to on-demand
4. Optimize access patterns (use Query instead of Scan)
5. Add appropriate GSIs for query patterns
```

### Data Loss Prevention
```
1. Enable point-in-time recovery (PITR)
2. Create regular backups
3. Enable deletion protection (manual process)
4. Use TTL carefully (test first)
5. Validate backup restore procedures regularly
```

## Monitoring Checklist

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| ThrottledRequests | > 0 | > 100 | Increase capacity/enable on-demand |
| ConsumedReadCapacity | > 80% provisioned | > 100% | Scale up or on-demand |
| ConsumedWriteCapacity | > 80% provisioned | > 100% | Scale up or on-demand |
| UserErrors | > 10 | > 100 | Check application code |
| SystemErrors | > 0 | > 10 | Contact AWS support |
| OnlineIndexPercentageProgress | < 100% | stuck | Wait or recreate index |
| AgeOfOldestUnreplicatedRecord | > 1 min | > 5 min | Check stream consumers |