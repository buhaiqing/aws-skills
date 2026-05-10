# SQS Troubleshooting

Common SQS error codes, recovery procedures.

## Error Code Reference

### QueueDoesNotExist
```
Error: Queue {{queue_name}} does not exist
```
**Resolution**:
```bash
# List queues
aws sqs list-queues --output json
```

### QueueDeletedRecently
```
Error: Queue recently deleted
```
**Cause**: Queue deleted within last 60 seconds.
**Resolution**: Wait 60 seconds and retry.

### MessageTooLarge
```
Error: Message exceeds 256KB
```
**Resolution**:
- Compress message
- Store in S3, send reference
- Split into multiple messages

### ReceiptHandleIsInvalid
```
Error: Invalid receipt handle
```
**Cause**: Message already deleted or expired.
**Resolution**: Re-receive message.

## Common Issues

### Messages Not Received
**Causes:**
- Queue empty
- Visibility timeout active
- Wrong queue URL

**Resolution**:
```bash
# Check queue depth
aws sqs get-queue-attributes \
  --queue-url {{queue_url}} \
  --attribute-names ApproximateNumberOfMessages
```

### Duplicate Messages
**Causes:**
- Standard queue (expected)
- Visibility timeout exceeded
- Consumer failed to delete

**Resolution:**
- Use FIFO queue for deduplication
- Implement idempotent processing
- Delete after successful processing

### Throttling
**Symptoms:**
- ThrottlingException
- Request rate too high

**Resolution:**
- Implement exponential backoff
- Batch operations
- Use multiple queues

## Recovery Procedures

### Queue Recovery
```
1. Check queue exists with get-queue-url
2. For deletion: confirm no messages
3. For creation: wait 60s after delete
4. Reconfigure DLQ if needed
```

### Message Recovery
```
1. Check DLQ for failed messages
2. Reprocess from DLQ
3. Monitor with CloudWatch
4. Adjust visibility timeout
```