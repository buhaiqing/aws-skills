---
name: aws-stepfunctions-ops
description: Use this skill when managing AWS Step Functions resources, creating/deleting
  state machines, starting/stopping executions, describing execution history, or configuring
  error handling; even if the user doesn't explicitly mention "Step Functions" or
  "state machine" but needs workflow orchestration.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with Step
  Functions permissions.
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
    accepts: ['health-check', 'rca', 'change-impact']
    produces_facts: ['state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Step Functions Ops Skill

AWS Step Functions operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create SM:       .stateMachineArn
# Describe SM:     .{stateMachineArn,name,status,definition}
# List SMs:        .stateMachines[].{stateMachineArn,name,creationDate}
# Start Exec:      .executionArn
# Describe Exec:   .{executionArn,status,output,startDate}
# Stop Exec:       Empty (success)
# Get History:     .events[].{id,type,timestamp}
```

## Trigger & Scope

### SHOULD Use When
- User requests state machine creation or deletion
- User needs to start/stop executions
- User asks about Step Functions
- User mentions "state machine", "workflow", "execution"
- User needs to describe execution history
- User asks about error handling or retries

### SHOULD NOT Use When
- Lambda operations only → delegate to: `aws-lambda-ops`
- EventBridge rules → delegate to: `aws-eventbridge-ops`
- Simple queue operations → delegate to: `aws-sqs-ops`

### Delegation
- Lambda → `aws-lambda-ops` (Lambda functions)
- IAM → `aws-iam-ops` (Execution role)
- CloudWatch → `aws-cloudwatch-ops` (Metrics)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use `us-east-1` if unset |
| `{{user.StateMachineName}}` | User input | Ask once; reuse |
| `{{user.StateMachineArn}}` | User input | Ask once; reuse |
| `{{user.ExecutionArn}}` | User input | Ask once; reuse |
| `{{user.RoleArn}}` | User input | Ask once; reuse |
| `{{user.Definition}}` | User input | ASL definition (JSON) |
| `{{output.ExecArn}}` | Last API response | Parse `.executionArn` |

## Execution Flow

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify IAM role and check state machine definition syntax.

**CLI (primary)**: `aws stepfunctions [command] --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Use `describe-state-machine` or `describe-execution` to confirm.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidDefinition (400) | Fix ASL syntax; retry once |
| StateMachineDoesNotExist | Verify SM ARN |
| ExecutionDoesNotExist | Verify execution ARN |
| Throttling (429) | Backoff, retry 3x |
| InternalError (5xx) | Retry 3x; HALT |

## Safety Gates

### Delete State Machine
```
⚠️ Deleting state machine will remove all executions and history.
Before proceeding:
1. Check for running executions via `list-executions`
2. Stop active executions via `stop-execution`
3. Confirm: Type DELETE {{user.StateMachineName}} to proceed.
```

## Related Skills

- `aws-lambda-ops` - Lambda functions
- `aws-iam-ops` - IAM roles
- `aws-cloudwatch-ops` - Metrics

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded state machine limits — use `describe-state-machine` / `list-state-machines`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-stepfunctions-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-state-machine` — IRREVERSIBLE; removes all executions and history; pre-flight `list-executions` for running executions; confirm `DELETE_SM <sm-name>`
- `stop-execution` — terminates a running execution; confirm `STOP_EXECUTION <execution-arn>`
- `update-state-machine` — changing definition could break running executions

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (stateMachineArn echoed from `describe-state-machine`), A9 (definition/input secrets masked), A10 (sts first command).

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

