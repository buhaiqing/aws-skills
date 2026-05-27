# AWS CLI Usage - SNS

AWS CLI commands for SNS operations. All commands use `--region {{r.region}} --output json`.

## Common JSON Paths (Centralized)

```
# Create Topic:   .TopicArn
# Publish:        .MessageId
# Subscribe:      .SubscriptionArn
# Unsubscribe:    Empty (success)
# List Topics:    .Topics[]
# List Subs:      .Subscriptions[].{SubscriptionArn,Protocol,Endpoint}
# Set Filter:     Empty (success)
```

## Topic Operations

### Create Topic
```bash
# Standard topic
aws sns create-topic --name {{u.name}}

# FIFO topic
aws sns create-topic --name {{u.name}}.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true
```

### Get Topic Attributes
```bash
aws sns get-topic-attributes --topic-arn {{u.arn}}
```

### List Topics
```bash
aws sns list-topics
```

### Delete Topic
```bash
aws sns delete-topic --topic-arn {{u.arn}}
```

## Subscription Operations

### Subscribe
```bash
# Email
aws sns subscribe --topic-arn {{u.arn}} --protocol email --notification-endpoint {{u.endpoint}}

# Lambda
aws sns subscribe --topic-arn {{u.arn}} --protocol lambda --notification-endpoint {{u.endpoint}}

# SQS
aws sns subscribe --topic-arn {{u.arn}} --protocol sqs --notification-endpoint {{u.endpoint}}

# HTTP/HTTPS
aws sns subscribe --topic-arn {{u.arn}} --protocol https --notification-endpoint {{u.endpoint}}
```

### List Subscriptions
```bash
aws sns list-subscriptions-by-topic --topic-arn {{u.arn}}
```

### Unsubscribe
```bash
aws sns unsubscribe --subscription-arn {{u.sub_arn}}
```

### Confirm Subscription
```bash
aws sns confirm-subscription --topic-arn {{u.arn}} --token {{u.token}}
```

## Message Operations

### Publish
```bash
# Simple message
aws sns publish --topic-arn {{u.arn}} --message "{{u.msg}}" --subject "{{u.subject}}"

# With message attributes
aws sns publish --topic-arn {{u.arn}} --message "{{u.msg}}" \
  --message-attributes '{"priority":{"DataType":"String","StringValue":"high"}}'
```

## Filter Policies

### Set Subscription Filter
```bash
aws sns set-subscription-attributes \
  --subscription-arn {{u.sub_arn}} \
  --attribute-name FilterPolicy \
  --attribute-value '{"priority":["high","critical"]}'
```

## Common Options

| Option | Description |
|--------|-------------|
| `--topic-arn` | Topic ARN |
| `--protocol` | `email\|sqs\|lambda\|http\|https\|sms` |
| `--notification-endpoint` | Subscriber endpoint |
| `--message` | Message body |
| `--subject` | Email subject |
| `--message-attributes` | Filterable key-value pairs |
| `--subscription-arn` | Subscription ARN |