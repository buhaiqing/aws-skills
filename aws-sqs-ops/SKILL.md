---
name: aws-sqs-ops
description: >-
  Use this skill when managing AWS SQS resources, creating/deleting queues,
  sending/receiving messages, configuring DLQs, setting queue attributes, or
  integrating with Lambda triggers; even if the user doesn't explicitly mention
  "SQS" or "queue" but needs message queuing functionality.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with SQS
  permissions.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-15"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS SQS Ops Skill

AWS SQS (Simple Queue Service) operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create Queue:       .QueueUrl
# List Queues:        .QueueUrls[]
# Get Queue URL:      .QueueUrl
# Send Message:       .MessageId
# Receive Messages:   .Messages[].{MessageId,ReceiptHandle,Body}
# Delete Message:     Empty (success)
# Get Attributes:     .Attributes
# Purge Queue:        Empty (success)
```

## Trigger & Scope

### SHOULD Use When
- User requests queue creation or deletion
- User needs to send/receive messages
- User asks about Dead Letter Queues (DLQ)
- User mentions "SQS", "queue", "message", "FIFO"
- User needs to configure queue attributes
- User asks about Lambda triggers for SQS

### SHOULD NOT Use When
- SNS topics → delegate to: `aws-sns-ops`
- EventBridge → delegate to: `aws-eventbridge-ops`
- Kinesis → delegate to: `aws-kinesis-ops`

### Delegation
- Lambda → `aws-lambda-ops` (SQS trigger)
- KMS → `aws-kms-ops` (queue encryption)
- CloudWatch → `aws-cloudwatch-ops` (metrics)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.QueueName}}` | User input | Ask once; reuse |
| `{{user.QueueUrl}}` | User input | Ask once; reuse |
| `{{user.MessageBody}}` | User input | Ask once; reuse |
| `{{user.ReceiptHandle}}` | User input | Ask once; reuse |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify queue exists via `get-queue-url`.

**CLI (primary)**: `aws sqs [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-queue-attributes` to confirm create/update. Poll max 60s for delete/purge.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix params; retry once |
| ResourceNotFound (404) | Verify queue name/URL |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Safety Gates

### Queue Deletion
```
⚠️ Queue deletion is irreversible. All messages in {{user.QueueName}} will be lost.
Confirm: Type DELETE {{user.QueueName}} to proceed.
```

### Queue Purge
```
⚠️ Purging {{user.QueueName}} will delete all messages immediately. No recovery possible.
Confirm: Type PURGE {{user.QueueName}} to proceed.
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)