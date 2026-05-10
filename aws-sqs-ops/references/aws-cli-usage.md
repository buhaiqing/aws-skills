# AWS CLI Usage - SQS

AWS CLI commands for SQS operations. All commands use `--output json`.

## Queue Operations

### Create Queue
```bash
# Standard queue
aws sqs create-queue \
  --queue-name {{user.QueueName}} \
  --attributes '{"VisibilityTimeout":"30","MessageRetentionPeriod":"345600"}' \
  --output json

# FIFO queue
aws sqs create-queue \
  --queue-name {{user.QueueName}}.fifo \
  --attributes '{"FifoQueue":"true","ContentBasedDeduplication":"true"}' \
  --output json
```

### Get Queue URL
```bash
aws sqs get-queue-url \
  --queue-name {{user.QueueName}} \
  --output json
```

### List Queues
```bash
aws sqs list-queues --output json
```

### Delete Queue
```bash
aws sqs delete-queue \
  --queue-url {{user.QueueUrl}} \
  --output json
```

## Message Operations

### Send Message
```bash
aws sqs send-message \
  --queue-url {{user.QueueUrl}} \
  --message-body "{{user.MessageBody}}" \
  --delay-seconds 0 \
  --output json

# With message attributes
aws sqs send-message \
  --queue-url {{user.QueueUrl}} \
  --message-body "{{user.MessageBody}}" \
  --message-attributes '{"type":{"DataType":"String","StringValue":"order"}}' \
  --output json
```

### Receive Message
```bash
aws sqs receive-message \
  --queue-url {{user.QueueUrl}} \
  --max-number-of-messages 10 \
  --visibility-timeout 30 \
  --wait-time-seconds 20 \
  --output json
```

### Delete Message
```bash
aws sqs delete-message \
  --queue-url {{user.QueueUrl}} \
  --receipt-handle {{user.ReceiptHandle}} \
  --output json
```

### Delete Message Batch
```bash
aws sqs delete-message-batch \
  --queue-url {{user.QueueUrl}} \
  --entries Id=msg1,ReceiptHandle={{handle1}} Id=msg2,ReceiptHandle={{handle2}} \
  --output json
```

## Queue Attributes

### Get Queue Attributes
```bash
aws sqs get-queue-attributes \
  --queue-url {{user.QueueUrl}} \
  --attribute-names All \
  --output json
```

### Set Queue Attributes
```bash
aws sqs set-queue-attributes \
  --queue-url {{user.QueueUrl}} \
  --attributes '{"VisibilityTimeout":"60","MessageRetentionPeriod":"86400"}' \
  --output json
```

## Queue Operations

### Purge Queue
```bash
aws sqs purge-queue \
  --queue-url {{user.QueueUrl}} \
  --output json
```

### Get Queue Attributes
```bash
aws sqs get-queue-attributes \
  --queue-url {{user.QueueUrl}} \
  --attribute-names ApproximateNumberOfMessages \
  --output json
```

## Common Options

```bash
--queue-url {{user.QueueUrl}}              # Queue URL
--queue-name {{user.QueueName}}            # Queue name
--message-body "{{user.MessageBody}}"      # Message content
--delay-seconds 0                          # Delay delivery (0-900)
--max-number-of-messages 10                  # Receive up to 10
--visibility-timeout 30                    # Visibility timeout (0-43200)
--wait-time-seconds 20                     # Long polling (0-20)
```