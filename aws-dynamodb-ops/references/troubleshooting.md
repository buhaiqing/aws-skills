# DynamoDB Troubleshooting

## Error Code Reference

### Table Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **TableAlreadyExists** | Table name exists | Use different name | [→](troubleshooting-details/table-errors.md) |
| **ResourceNotFoundException** | Deleted/wrong name/wrong region | `list-tables`, check region | [→](troubleshooting-details/table-errors.md) |
| **LimitExceededException** | Quota limit reached | Request increase or delete unused tables | - |

### Capacity/Throughput Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **ProvisionedThroughputExceededException** | Request rate exceeds capacity | Backoff or increase capacity | [→](troubleshooting-details/capacity-errors.md) |

### Conditional Check Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| **ConditionalCheckFailedException** | Condition expression evaluated false | Check item state before conditional write |

### Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Attribute type mismatch | Wrong DynamoDB format | Use correct: `{"S": "value"}` |
| Missing key attribute | Put/Get without full key | Include partition + sort key |
| Invalid expression syntax | Malformed expression | Check syntax |
| Number exceeds precision | Large numbers | Use string for large numbers |
| Empty string not allowed | Empty string value | Remove or use placeholder |

### Size Limit Errors

| Error | Cause | Resolution | Details |
|-------|-------|------------|---------|
| **ItemCollectionSizeLimitExceededException** | LSI collection exceeds 10GB | Redesign keys or use GSI | [→](troubleshooting-details/size-errors.md) |
| 400KB item limit | Item exceeds max size | Compress, split, or store in S3 | [→](troubleshooting-details/size-errors.md) |

### Transaction Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| **TransactionConflictException** | Concurrent modification of same items | Retry with backoff |
| **IdempotentParameterMismatchException** | Same client token for different requests | Use unique token per transaction |

## Throttling Handling

| Method | Action |
|--------|--------|
| **Immediate** | Exponential backoff: `delay = min(2^attempt * 0.1 + random(0, 0.1), 60)`, max 10 retries |
| **Short-term** | Enable auto-scaling via `application-autoscaling register-scalable-target` |
| **Long-term** | Switch to on-demand: `update-table --billing-mode PAY_PER_REQUEST` |

**Detailed:** [Capacity Errors](troubleshooting-details/capacity-errors.md)

## Hot Partition Issues

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| High `ProvisionedThroughputExceededException` | Enable Contributor Insights → top contributors | Write sharding, random suffix, or high-cardinality keys |

**Detailed:** [Hot Partitions](troubleshooting-details/hot-partitions.md)

## GSI Issues

| Symptom | Resolution |
|---------|------------|
| GSI backlogged / lagging | Check `IndexStatus` → wait for CREATING to finish |
| Frequent base table lookups | Recreate GSI with `ProjectionType: ALL` |

**Detailed:** [GSI Issues](troubleshooting-details/gsi-issues.md)

## Stream / TTL / Backup Issues

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| Stream not triggering Lambda | Check stream status + Lambda event source mapping | Verify role permissions, timeout |
| TTL not deleting items | `describe-time-to-live`, check attribute format | Must be Number with epoch seconds |
| Backup creation hanging | `describe-backup` → check status | Wait for large tables |
| PITR not available | PITR not enabled or >35 days | `update-continuous-backups --point-in-time-recovery-specification` |

**Detailed:** [Stream & TTL](troubleshooting-details/stream-ttl.md)

## Recovery Flow

```
1. Identify error from CloudWatch/exception
2. describe-table → check status
3. Throttling → backoff or scale up
4. Validation → fix input params
5. Size → split or S3
6. Max 3 retries for transient; HALT for data loss
```

## Monitoring Checklist

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| ThrottledRequests | > 0 | > 100 | Increase capacity/enable on-demand |
| ConsumedReadCapacity | > 80% provisioned | > 100% | Scale up or on-demand |
| ConsumedWriteCapacity | > 80% provisioned | > 100% | Scale up or on-demand |
| UserErrors | > 10 | > 100 | Check application code |
| SystemErrors | > 0 | > 10 | Contact AWS support |
| OnlineIndexPercentageProgress | < 100% | stuck | Wait or recreate |
| AgeOfOldestUnreplicatedRecord | > 1 min | > 5 min | Check stream consumers |