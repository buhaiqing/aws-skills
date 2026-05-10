# AWS CLI Usage - SNS

AWS CLI commands for SNS operations. All commands use `--output json`.

## Topic Operations

### Create Topic
```bash
# Standard topic
aws sns create-topic \
  --name {{user.TopicName}} \
  --output json

# FIFO topic
aws sns create-topic \
  --name {{user.TopicName}}.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true \
  --output json
```

### Get Topic Attributes
```bash
aws sns get-topic-attributes \
  --topic-arn {{user.TopicArn}} \
  --output json
```

### List Topics
```bash
aws sns list-topics --output json
```

### Delete Topic
```bash
aws sns delete-topic \
  --topic-arn {{user.TopicArn}} \
  --output json
```

## Subscription Operations

### Subscribe
```bash
# Email subscription
aws sns subscribe \
  --topic-arn {{user.TopicArn}} \
  --protocol email \
  --notification-endpoint {{user.Email}} \
  --output json

# Lambda subscription
aws sns subscribe \
  --topic-arn {{user.TopicArn}} \
  --protocol lambda \
  --notification-endpoint {{user.LambdaArn}} \
  --output json

# SQS subscription
aws sns subscribe \
  --topic-arn {{user.TopicArn}} \
  --protocol sqs \
  --notification-endpoint {{user.QueueArn}} \
  --output json
```

### List Subscriptions
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn {{user.TopicArn}} \
  --output json
```

### Unsubscribe
```bash
aws sns unsubscribe \
  --subscription-arn {{user.SubscriptionArn}} \
  --output json
```

### Confirm Subscription
```bash
aws sns confirm-subscription \
  --topic-arn {{user.TopicArn}} \
  --token {{user.Token}} \
  --output json
```

## Message Operations

### Publish
```bash
# Simple message
aws sns publish \
  --topic-arn {{user.TopicArn}} \
  --message "{{user.Message}}" \
  --subject "{{user.Subject}}" \
  --output json

# Message with attributes
aws sns publish \
  --topic-arn {{user.TopicArn}} \
  --message "{{user.Message}}" \
  --message-attributes '{"priority":{"DataType":"String","StringValue":"high"}}' \
  --output json
```

## Filter Policies

### Set Subscription Filter
```bash
aws sns set-subscription-attributes \
  --subscription-arn {{user.SubscriptionArn}} \
  --attribute-name FilterPolicy \
  --attribute-value '{"priority":["high","critical"]}' \
  --output json
```

## Common Options

```bash
--topic-arn {{user.TopicArn}}           # Topic ARN
--protocol email|sqs|lambda|http|sms    # Subscription protocol
--notification-endpoint {{endpoint}}      # Subscriber endpoint
--message "{{user.Message}}"            # Message body
--subject "{{user.Subject}}"            # Email subject
```