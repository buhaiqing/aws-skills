# SQS Core Concepts

AWS SQS architecture, components, and operational concepts.

## Service Overview

**AWS SQS** - Fully managed message queuing service.

**Key Benefits:**
- Decouples application components
- Scalable and reliable
- No message loss
- Flexible consumption patterns

## Queue Types

### Standard Queue
- **Characteristics**: Best effort ordering, at-least-once delivery
- **Throughput**: Nearly unlimited
- **Use case**: High throughput, order not critical

### FIFO Queue
- **Characteristics**: First-in-first-out, exactly-once processing
- **Throughput**: 300 msg/sec (without batching)
- **Use case**: Order critical, duplicates not allowed

## Message Lifecycle

### States
1. **Sent** → Message in queue
2. **Received** → Consumer processing
3. **Invisible** → Visibility timeout
4. **Deleted** → Removed from queue
5. **Dead Letter** → After max receives

### Visibility Timeout
- Time message is invisible after receive
- Prevents duplicate processing
- Default: 30 seconds
- Max: 12 hours

### Delay Queue
- Delays message delivery
- Default: 0 seconds
- Max: 15 minutes

## Dead Letter Queue (DLQ)

### Purpose
Store messages that failed processing.

### Configuration
- **maxReceiveCount**: Max receives before DLQ
- **dlq**: Target dead letter queue

### Use Cases
- Debug failed messages
- Reprocess later
- Alert on failures

## Quotas

| Resource | Default | Notes |
|----------|---------|-------|
| Message size | 256 KB | Body + attributes |
| Retention | 14 days | 1 min - 14 days |
| Inflight messages | 120,000 | Standard queue |
| FIFO inflight | 20,000 | Per message group |
| Delay | 15 min | Per queue or message |

## Pricing

- **Requests**: $0.40 per million
- **Data transfer**: Standard rates
- **First 1 million requests/month**: Free

## Best Practices

### Queue Design
- Use dead letter queues
- Set appropriate visibility timeout
- Enable CloudWatch monitoring
- Use long polling

### Message Processing
- Delete after successful processing
- Handle failures gracefully
- Implement idempotency
- Use message attributes for metadata

### Cost Optimization
- Batch operations when possible
- Delete unnecessary messages
- Set appropriate retention periods
- Use standard queues when order not needed