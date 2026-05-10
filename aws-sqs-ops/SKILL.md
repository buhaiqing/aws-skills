# AWS SQS Ops Skill

AWS SQS (Simple Queue Service) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests queue creation or deletion
- User needs to send/receive messages
- User asks about Dead Letter Queues (DLQ)
- User mentions "SQS", "queue", "message", "FIFO"
- User needs to configure queue attributes
- User asks about Lambda triggers for SQS

**SHOULD-NOT activate when:**
- SNS topics (use `aws-sns-ops`)
- EventBridge (use `aws-eventbridge-ops`)
- Kinesis (use `aws-kinesis-ops`)

**Delegation:**
- Lambda → `aws-lambda-ops` (SQS trigger)
- KMS → `aws-kms-ops` (queue encryption)
- CloudWatch → `aws-cloudwatch-ops` (metrics)

## Scope

| Operation | Supported | Safety Gate |
|-----------|-----------|-------------|
| Create Queue | Yes | None |
| Delete Queue | Yes | **Human confirmation** |
| Send Message | Yes | None |
| Receive Message | Yes | None |
| Delete Message | Yes | None |
| Purge Queue | Yes | **Human confirmation** |
| Set Queue Attributes | Yes | None |
| Configure DLQ | Yes | None |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Environment | Never ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Environment | Never ask user |
| `{{env.AWS_DEFAULT_REGION}}` | Environment | us-east-1 |
| `{{user.QueueName}}` | User input | my-queue |
| `{{user.QueueUrl}}` | User input | https://sqs... |
| `{{user.MessageBody}}` | User input | Message content |
| `{{user.ReceiptHandle}}` | User input | Message receipt handle |

## Execution Flow

### Pre-flight
```
1. Check AWS CLI: aws --version
2. Validate credentials: aws sts get-caller-identity
3. Verify queue exists: aws sqs get-queue-url --queue-name {{user.QueueName}}
4. Check permissions
```

### Execute (Primary: CLI)
```
aws sqs send-message \
  --queue-url {{user.QueueUrl}} \
  --message-body "{{user.MessageBody}}" \
  --output json
```

### Execute (Fallback: boto3)
```python
import boto3
sqs = boto3.client('sqs', region_name='{{env.AWS_DEFAULT_REGION}}')
response = sqs.send_message(
    QueueUrl='{{user.QueueUrl}}',
    MessageBody='{{user.MessageBody}}'
)
```

## Safety Gates

### Queue Deletion
```
BEFORE delete-queue:
1. Display: "Deleting {{user.QueueName}} will remove all messages"
2. Ask: "Type 'DELETE {{user.QueueName}}' to confirm"
```

### Queue Purge
```
BEFORE purge-queue:
1. Display: "Purging {{user.QueueName}} will delete all messages (no recovery)"
2. Ask: "Type 'PURGE {{user.QueueName}}' to confirm"
```

## Output Convention

Key JSON paths:
- `.QueueUrl` - queue URL
- `.QueueArn` - queue ARN
- `.MessageId` - sent message ID
- `.ReceiptHandle` - message receipt handle
- `.Messages[].Body` - message body
- `.Messages[].ReceiptHandle` - receipt handle for deletion

## Related Skills

- `aws-lambda-ops` - SQS trigger
- `aws-kms-ops` - Queue encryption
- `aws-cloudwatch-ops` - Monitoring

## Reference Files

- `references/aws-cli-usage.md`
- `references/boto3-sdk-usage.md`
- `references/core-concepts.md`
- `references/troubleshooting.md`
- `assets/example-config.yaml`