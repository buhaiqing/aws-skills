# SNS Core Concepts

AWS SNS architecture, components, and operational concepts.

## Service Overview

**AWS SNS** - Fully managed pub/sub messaging service.

**Key Benefits:**
- Decoupled messaging
- Multiple protocol support
- Message filtering
- High throughput
- Serverless integration

## Topics

### Standard Topic
- **Characteristics**: Best-effort ordering, at-least-once delivery
- **Throughput**: Nearly unlimited
- **Use case**: High volume, order not critical

### FIFO Topic
- **Characteristics**: First-in-first-out, exactly-once delivery
- **Throughput**: 300 msg/sec
- **Use case**: Order critical

## Subscription Protocols

### Email/Email-JSON
- **Use**: Email notifications
- **Confirmation**: Required
- **Format**: Plain text or JSON

### HTTP/HTTPS
- **Use**: Webhook notifications
- **Confirmation**: Required
- **Delivery**: POST request

### SQS
- **Use**: Queue-based processing
- **Confirmation**: Automatic
- **Format**: Message envelope

### Lambda
- **Use**: Serverless processing
- **Confirmation**: Automatic
- **Invocation**: Event trigger

### SMS
- **Use**: Text notifications
- **Confirmation**: Not required
- **Limits**: Per-country regulations

## Message Filtering

### Filter Policies
JSON policy to filter messages.

```json
{
  "priority": ["high", "critical"],
  "source": ["payment", "security"]
}
```

### Message Attributes
Key-value pairs for filtering.

## Message Delivery

### Retry Policy
- **Immediate**: 0 seconds
- **Retries**: 3 times
- **Backoff**: Exponential
- **Max**: 20 minutes between retries

### Dead Letter Queue (DLQ)
Failed deliveries after max retries.

## Quotas

| Resource | Default | Notes |
|----------|---------|-------|
| Topics per account | 100,000 | - |
| Subscriptions per topic | 10,000,000 | - |
| Message size | 256 KB | Body + attributes |
| Message retention | None | Must deliver or fail |

## Pricing

- **Topic operations**: $0.50 per million
- **Notifications**: $0.50-$2.00 per million
- **Mobile push**: $0.50 per million
- **SMS**: Variable by country
- **Email**: $2.00 per 100,000

## Best Practices

### Topic Design
- Use descriptive names
- Enable encryption
- Use FIFO for order critical
- Configure DLQs

### Subscription Management
- Use filter policies
- Monitor delivery status
- Handle bounces
- Confirm email subscriptions

### Message Patterns
- Use message attributes
- Implement idempotency
- Handle retries gracefully
- Monitor with CloudWatch