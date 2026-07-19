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
    produces_facts: ['metric', 'event', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

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
- Kinesis data streaming → out of scope; use Kinesis CLI/SDK directly

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

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded queue attributes/limits — use `get-queue-attributes` / `list-queues`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-sqs-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-queue` — IRREVERSIBLE; all messages lost; confirm `DELETE_QUEUE <queue-name>`
- `purge-queue` — all messages deleted immediately; confirm `PURGE_QUEUE <queue-name>`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (QueueUrl echoed from `get-queue-url`), A9 (MessageBody secrets masked), A10 (sts first command).

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

