---
name: aws-eventbridge-ops
description: >-
  Use when the user needs to manage Amazon EventBridge resources — event
  buses, rules, targets, API destinations, connections, archives, event
  replay, EventBridge Scheduler schedules, or EventBridge Pipes; user
  mentions "EventBridge", "event bus", "event rule", "scheduler",
  "event pipe", "target", "API destination", or "event replay".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to EventBridge endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-ec2-ops              # EC2 event targets (RunCommand, etc.)
    - aws-lambda-ops           # Lambda function targets
    - aws-sqs-ops              # SQS queue targets
    - aws-sns-ops              # SNS topic targets
    - aws-stepfunctions-ops    # Step Functions targets
    - aws-iam-ops              # Execution role for targets
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'change-impact']
    produces_facts: ['event', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS EventBridge Operations Skill

Use for EventBridge buses, rules, targets, Scheduler schedules, Pipes, archives, replays, API destinations, connections, routing, and event-driven automation. Detailed commands remain in references.

## Common JSON Paths

Rule: .{Name,Arn,EventPattern,ScheduleExpression,State,EventBusName}
Rules: .Rules[].{Name,Arn,State,EventBusName}
Targets: .Targets[].{Id,Arn,RoleArn,Input,InputPath,InputTransformer}
Buses: .EventBuses[].{Name,Arn,Policy}
Schedule: .{Arn,State,ScheduleExpression,Target}
Pipe: .{Arn,CurrentState,Source,Target}
Archive: .{ArchiveArn,State,EventCount,SizeBytes}

## Trigger & Scope

### SHOULD Use When
EventBridge buses/rules/targets, Scheduler, Pipes, archives/replays, API destinations, connections, schedules, or event routing.

### SHOULD NOT Use When
SNS topics → `aws-sns-ops`; SQS queues → `aws-sqs-ops`; Lambda function CRUD → `aws-lambda-ops`; Step Functions workflows → `aws-stepfunctions-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.rule_name}}`, `{{user.bus_name}}`, `{{user.target_id}}` | User input | Bus/rule/target IDs |
| `{{user.schedule_name}}`, `{{user.pipe_name}}`, `{{user.archive_name}}` | User input | Scheduler/Pipe/archive IDs |
| `{{user.api_dest_name}}`, `{{user.conn_name}}` | User input | API destination/connection IDs |
| `{{output.*}}` | API response | Reuse ARNs and target IDs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify bus/rule/target ownership, IAM role, downstream target, references, schedules, pipes, archives, and connection users. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back routes/state; recover with bounded retries and halt on access, quota, or unresolved dependencies. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Modify rule/targets | Diff routing and downstream impact; validate target invocation | Token for production route changes |
| Remove targets/delete rule | List targets; remove explicitly; then delete rule | `REMOVE_TARGETS <rule>` and `DELETE_RULE <name>` |
| Delete event bus | List and delete every rule first | `DELETE_BUS <name>` |
| Delete schedule/pipe | Inspect target and event-flow impact | `DELETE_SCHEDULE <name>` / `DELETE_PIPE <name>` |
| Delete archive | Show event count/size and irreversible loss | `DELETE_ARCHIVE <name>` |
| Delete API destination | Verify no rules reference it | `DELETE_API_DEST <name>` |
| Delete connection | Verify no API destinations reference it | `DELETE_CONNECTION <name>` |

Mask API keys, connection auth parameters, event payload secrets, headers, and personal data in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live quotas/routes, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for routing/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
