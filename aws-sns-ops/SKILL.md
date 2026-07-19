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
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
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
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
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
| Create Topic | `aws sns create-topic --name {{user.name}}` | None |
| Delete Topic | `aws sns delete-topic --topic-arn {{user.arn}}` | **Human confirmation** |
| List Topics | `aws sns list-topics` | None |
| Publish Message | `aws sns publish --topic-arn {{user.arn}} --message "{{user.msg}}"` | None |
| Subscribe | `aws sns subscribe --topic-arn {{user.arn}} --protocol {{user.proto}} --notification-endpoint {{user.endpoint}}` | None |
| Unsubscribe | `aws sns unsubscribe --subscription-arn {{user.sub_arn}}` | None |
| Set Filter Policy | `aws sns set-subscription-attributes --subscription-arn {{user.sub_arn}} --attribute-name FilterPolicy --attribute-value '{{user.policy}}'` | None |
| Confirm Subscription | `aws sns confirm-subscription --topic-arn {{user.arn}} --token {{user.token}}` | None |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.region}}` | User input or `{{env.AWS_DEFAULT_REGION}}` | Default `us-east-1` |
| `{{user.name}}` | User input | Ask once; reuse |
| `{{user.arn}}` | User input | Ask once; reuse |
| `{{user.proto}}` | User input | email, sqs, lambda, http, sms |
| `{{user.endpoint}}` | User input | email / Lambda ARN / SQS ARN |
| `{{user.sub_arn}}` | User input | Subscription ARN |
| `{{user.msg}}` | User input | Message body |
| `{{user.subject}}` | User input | Optional email subject |
| `{{user.token}}` | User input | Confirmation token |
| `{{output.*}}` | Last API response | Parse from JSON output |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify topic exists via `get-topic-attributes`.

**CLI (primary)**: `aws sns [command] --region {{user.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

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
⚠️ Deleting {{user.name}} will remove all subscriptions. IRREVERSIBLE.
Type DELETE {{user.arn}} to confirm.
```

## Related Skills

- `aws-lambda-ops` — Lambda subscription
- `aws-sqs-ops` — SQS subscription
- `aws-kms-ops` — Topic encryption

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded protocol lists/limits — use `list-topics` / `get-topic-attributes`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

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

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

