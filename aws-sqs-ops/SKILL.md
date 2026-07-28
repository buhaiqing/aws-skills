---
name: aws-sqs-ops
description: Use this skill when managing AWS SQS resources, creating/deleting queues,
  sending/receiving messages, configuring DLQs, setting queue attributes, or integrating
  with Lambda triggers; even if the user doesn't explicitly mention "SQS" or "queue"
  but needs message queuing functionality.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with SQS
  permissions.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  gcl: {enabled: true, class: required, max_iter: 2, rubric_version: v1, rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md, pilot: false}
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca']
    produces_facts: ['metric', 'event', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS SQS Ops Skill

AWS SQS (Simple Queue Service) operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
CreateQueue: .QueueUrl
ListQueues: .QueueUrls[]
GetQueueUrl: .QueueUrl
SendMessage: .MessageId
ReceiveMessages: .Messages[].{MessageId,ReceiptHandle,Body}
GetAttributes: .Attributes
```

## Trigger & Scope

### SHOULD Use When
Use for SQS queues, messages, DLQs, FIFO, attributes, or Lambda integration.

### SHOULD NOT Use When
SNS → `aws-sns-ops`; EventBridge → `aws-eventbridge-ops`; Kinesis streaming → direct CLI/SDK.

### Delegation
Lambda → `aws-lambda-ops`; KMS → `aws-kms-ops`; metrics → `aws-cloudwatch-ops`.

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

## Token Efficiency

TE-1…TE-6 apply; query live attributes/limits, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Quality Gate (GCL)
Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Confirm `DELETE_QUEUE <queue-name>` before `delete-queue` and `PURGE_QUEUE <queue-name>` before `purge-queue`; apply A7, A8, A9, A10 from `gcl-spec.md` §8.

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
