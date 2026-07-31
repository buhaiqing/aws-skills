---
name: aws-sns-ops
description: Use this skill when managing AWS SNS resources, creating/deleting topics,
  managing subscriptions, publishing messages, configuring message filtering, or integrating
  with Lambda/SQS; even if the user doesn't explicitly mention "SNS" or "topic" but
  needs pub/sub notification functionality.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with SNS
  permissions.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: '2026-07-31'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  gcl: {enabled: true, class: required, max_iter: 2, rubric_version: v1, rubric_ref: references/rubric.md, prompts_ref: references/prompt-templates.md, pilot: false}
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca']
    produces_facts: ['metric', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS SNS Ops Skill

AWS SNS (Simple Notification Service) operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create Topic:   .TopicArn
# Get Attributes: .Attributes
# Publish:        .MessageId
# Subscribe:      .SubscriptionArn
# List Subs:      .Subscriptions[].{SubscriptionArn,Protocol,Endpoint}
```

## Trigger & Scope

### SHOULD Use When
Use for SNS topics, subscriptions, notifications, filtering, publishing, or Lambda/SQS integration.

### SHOULD NOT Use When
SQS → `aws-sqs-ops`; EventBridge → `aws-eventbridge-ops`; direct messaging → application-level messaging.

### Delegation
Lambda → `aws-lambda-ops`; SQS → `aws-sqs-ops`; KMS → `aws-kms-ops`.

## Scope & Quick Reference

`create-topic` · `delete-topic` ⚠️ · `list-topics` · `publish` · `subscribe` · `unsubscribe` ⚠️ · `set-subscription-attributes` (filter policy) · `confirm-subscription`. Full CLI: [aws-cli-usage.md](references/aws-cli-usage.md).

## Variable Convention

| Placeholder | Source | Action |
|-------------|--------|--------|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.region}}`, `{{user.name}}`, `{{user.arn}}` | User/env | Ask once; reuse |
| `{{user.proto}}`, `{{user.endpoint}}`, `{{user.sub_arn}}`, `{{user.msg}}`, `{{user.subject}}` | User input | Operation payloads |
| `{{output.*}}` | API response | Parse paths declared above |

## Execution Flow

Pre-flight (`aws --version` + `aws sts get-caller-identity`) → Execute (CLI primary `--output json`; boto3 fallback after 3 failures — [aws-cli-usage.md](references/aws-cli-usage.md) / [boto3-sdk-usage.md](references/boto3-sdk-usage.md)) → Validate (`get-topic-attributes` / `list-subscriptions-by-topic`) → Recover on 400/404/429/5xx per [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Delete topic | Warn: removes all subscriptions; irreversible | `confirm=DELETE_TOPIC {{user.arn}}` |
| Unsubscribe | Verify subscription ARN | `confirm=UNSUBSCRIBE {{user.sub_arn}}` |

## Related Skills

`aws-lambda-ops` (Lambda subscription) · `aws-sqs-ops` (SQS subscription) · `aws-kms-ops` (topic encryption).

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md). JSON paths in `## Common JSON Paths` (TE-4); no hardcoded protocol lists (TE-1); error tables in references/ (TE-3).

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md) · [integration.md](../aws-skill-generator/references/integration.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate` (`request_id`, `parent_intent`, `action_mode`, `decision_tier`, `scope.resource_ids`); deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
