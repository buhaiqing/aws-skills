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
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment: [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-lambda-ops
    - aws-sqs-ops
    - aws-sns-ops
    - aws-cloudwatch-ops
    - aws-iam-ops
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
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
CreateStateMachine: .stateMachineArn
DescribeStateMachine: .{stateMachineArn,name,status,definition}
ListStateMachines: .stateMachines[].{stateMachineArn,name,creationDate}
StartExecution: .executionArn
DescribeExecution: .{executionArn,status,output,startDate}
GetHistory: .events[].{id,type,timestamp}
```

## Trigger & Scope

### SHOULD Use When
Use for Step Functions state machines, executions, histories, workflow retries, or error handling.

### SHOULD NOT Use When
Lambda-only → `aws-lambda-ops`; EventBridge → `aws-eventbridge-ops`; queues → `aws-sqs-ops`.

### Delegation
Lambda → `aws-lambda-ops`; IAM → `aws-iam-ops`; metrics → `aws-cloudwatch-ops`.

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
3. Confirm: `confirm=DELETE_SM {{user.StateMachineName}}` to proceed.
```

## Token Efficiency
TE-1…TE-6 apply; query live state-machine data, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Quality Gate (GCL)
Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Before deletion list and stop running executions, then confirm `confirm=DELETE_SM <sm-name>`; confirm `confirm=STOP_EXECUTION <execution-arn>` and definition updates; apply A7–A10 from `gcl-spec.md` §8.

## Reference Files
[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](../aws-skill-generator/references/integration.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive ops; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
