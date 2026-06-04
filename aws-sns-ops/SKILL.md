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
  version: 1.1.0
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
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
- User requests topic creation or deletion
- User needs to manage subscriptions
- User asks about SNS notifications
- User mentions "SNS", "topic", "subscription", "notification"
- User needs to configure message filtering
- User asks about Lambda/SQS integration

### SHOULD NOT Use When
- SQS operations → delegate to: `aws-sqs-ops`
- EventBridge → delegate to: `aws-eventbridge-ops`
- Direct messaging → delegate to: application-level messaging

### Delegation
- Lambda → `aws-lambda-ops` (SNS trigger)
- SQS → `aws-sqs-ops` (SQS subscription)
- KMS → `aws-kms-ops` (topic encryption)

## Scope & Quick Reference

| Operation | CLI | Safety Gate |
|-----------|-----|-------------|
| Create Topic | `aws sns create-topic --name {{u.name}}` | None |
| Delete Topic | `aws sns delete-topic --topic-arn {{u.arn}}` | **Human confirmation** |
| List Topics | `aws sns list-topics` | None |
| Publish Message | `aws sns publish --topic-arn {{u.arn}} --message "{{u.msg}}"` | None |
| Subscribe | `aws sns subscribe --topic-arn {{u.arn}} --protocol {{u.proto}} --notification-endpoint {{u.endpoint}}` | None |
| Unsubscribe | `aws sns unsubscribe --subscription-arn {{u.sub_arn}}` | None |
| Set Filter Policy | `aws sns set-subscription-attributes --subscription-arn {{u.sub_arn}} --attribute-name FilterPolicy --attribute-value '{{u.policy}}'` | None |
| Confirm Subscription | `aws sns confirm-subscription --topic-arn {{u.arn}} --token {{u.token}}` | None |

## Placeholder Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{r.region}}` | User input or `{{env.AWS_DEFAULT_REGION}}` | Default `us-east-1` |
| `{{u.name}}` | User input | Ask once; reuse |
| `{{u.arn}}` | User input | Ask once; reuse |
| `{{u.proto}}` | User input | email, sqs, lambda, http, sms |
| `{{u.endpoint}}` | User input | email / Lambda ARN / SQS ARN |
| `{{u.sub_arn}}` | User input | Subscription ARN |
| `{{u.msg}}` | User input | Message body |
| `{{u.subject}}` | User input | Optional email subject |
| `{{u.token}}` | User input | Confirmation token |
| `{{o.*}}` | Last API response | Parse from JSON output |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify topic exists via `get-topic-attributes`.

**CLI (primary)**: `aws sns [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `get-topic-attributes` or `list-subscriptions-by-topic` to confirm.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameter (400) | Fix args; retry once |
| NotFound (404) | Verify topic/subscription exists |
| EndpointDisabled | Check endpoint validity; update or remove subscription |
| Throttling (429) | Backoff, retry 3x |
| InternalFailure (5xx) | Retry 3x; HALT |

## Safety Gates

### Topic Deletion
```
⚠️ Deleting {{u.name}} will remove all subscriptions. IRREVERSIBLE.
Type DELETE {{u.arn}} to confirm.
```

## Related Skills

- `aws-lambda-ops` — Lambda subscription
- `aws-sqs-ops` — SQS subscription
- `aws-kms-ops` — Topic encryption

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-sns-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-topic` — IRREVERSIBLE; removes all subscriptions; confirm `DELETE_TOPIC <topic-arn>`
- `unsubscribe` — removes subscriber from topic; confirm with user

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (TopicArn echoed from `list-topics` / `get-topic-attributes`), A9 (MessageBody secrets masked), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)