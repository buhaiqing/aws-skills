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
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'change-impact']
    produces_facts: ['event', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS EventBridge Operations Skill

## Common JSON Paths (Centralized)

```
# Event Buses:  .EventBuses[].{Name,Arn,EventBusName,Policy,Permission,CreationTime}
# Rules:        .Rules[].{Name,Arn,EventBusName,EventPattern,State,ScheduleExpression,ManagedBy,RoleArn}
# Targets:      .Targets[].{Id,Arn,RoleArn,Input,InputPath,DlqArn,RetryPolicy.{MaximumRetryAttempts,MaximumEventAgeInSeconds}}
# Connections:  .Connections[].{Name,ConnectionArn,AuthorizationType,CreationTime,ConnectionState}
# API Dests:    .ApiDestinations[].{Name,ApiDestinationArn,ConnectionArn,InvocationEndpoint,HttpMethod,InvocationRateLimitPerSecond}
# Archives:     .Archives[].{ArchiveName,EventSourceArn,RetentionDays,SizeBytes,EventCount,State}
# Replays:      .Replays[].{ReplayName,EventSourceArn,State,EventStartTime,EventEndTime,ReplayStartTime,ReplayEndTime}
# Schedules:    .Schedules[].{Name,GroupName,State,ScheduleExpression,Target.{Arn,RoleArn},FlexibleTimeWindow.{Mode,MaximumWindowInMinutes},CreationDate}
# Schedule Groups: .ScheduleGroups[].{Name,Arn,CreationDate,State}
# Pipes:         .Pipes[].{Name,Arn,Source,Target,RoleArn,State,CreationTime,LastModifiedTime,DesiredState}
```

## Overview

Serverless event bus for AWS services, SaaS partners, and custom apps.
Covers EventBus, Rules, Targets, API Destinations, Connections, Archives/Replay, Scheduler, Pipes.

## Trigger & Scope

### SHOULD Use When
- User mentions "EventBridge", "event bus", "event rule", "event pattern"
- Task involves **event buses** (create, describe, delete, permissions)
- Task involves **rules + targets** (put, describe, delete, remove targets)
- Task involves **API destinations** or **connections** (auth, REST endpoints)
- Task involves **event archives** and **replay**
- Task involves **EventBridge Scheduler** (create/delete schedule)
- Task involves **EventBridge Pipes** (source-target plumbing)
- Keywords: eventbridge, event-bus, event-rule, event-pattern, scheduler, pipe, api-destination, archive, replay, target

### SHOULD NOT Use When
- IAM execution roles → delegate to: `aws-iam-ops`
- Lambda function code → delegate to: `aws-lambda-ops`
- SQS queue config → delegate to: `aws-sqs-ops`
- SNS topic config → delegate to: `aws-sns-ops`
- Step Functions state machine → delegate to: `aws-stepfunctions-ops`

## Variable Convention

| Placeholder | Source | Notes |
|-------------|--------|-------|
| `{{env.AWS_ACCESS_KEY_ID}}` / `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Default `us-east-1` if unset |
| `{{user.region}}` | User | Ask once; reuse |
| `{{user.bus_name}}` / `{{user.rule_name}}` / `{{user.target_id}}` | User | Event bus (default: `default`), rule name, target id |
| `{{user.target_arn}}` / `{{user.target_role_arn}}` | User | Resource ARN + execution role ARN |
| `{{user.event_pattern}}` / `{{user.schedule_expr}}` | User | JSON event pattern or rate/cron expression |
| `{{user.conn_name}}` / `{{user.api_dest_name}}` / `{{user.api_dest_endpoint}}` | User | Connection name, API destination name + URL |
| `{{user.archive_name}}` / `{{user.replay_name}}` | User | Archive / replay name |
| `{{user.schedule_name}}` / `{{user.pipe_name}}` | User | Schedule / pipe name |
| `{{output.rule_arn}}` | API | Parse: `.Rules[0].Arn` |
| `{{output.bus_arn}}` | API | Parse: `.EventBuses[0].Arn` |

## Execution Flow Pattern

Every operation: **Pre-flight** → **Execute** (CLI, boto3 fallback) → **Validate** → **Recover**.

### Common Pre-flight (all ops)

```bash
aws --version && aws sts get-caller-identity --output json
```

### Create Event Rule

Pre-flight: `aws events describe-event-bus --name "{{user.bus_name}}"`
```bash
aws events put-rule \
  --name "{{user.rule_name}}" \
  --event-bus-name "{{user.bus_name}}" \
  --event-pattern '{{"source": ["aws.ec2"], "detail-type": ["EC2 Instance State-change Notification"]}}' \
  --state ENABLED \
  --region "{{user.region}}" --output json
```
Validate: `aws events describe-rule --name "{{user.rule_name}}" --event-bus-name "{{user.bus_name}}"`

### Add Targets

```bash
aws events put-targets \
  --rule "{{user.rule_name}}" \
  --event-bus-name "{{user.bus_name}}" \
  --targets '[{"Id":"{{user.target_id}}","Arn":"{{user.target_arn}}","RoleArn":"{{user.target_role_arn}}"}]' \
  --region "{{user.region}}" --output json
```

### Delete Rule

**Safety Gate**: `confirm=DELETE_RULE {{user.rule_name}}`. Must remove targets first.
```bash
aws events list-targets-by-rule --rule "{{user.rule_name}}" --event-bus-name "{{user.bus_name}}" --region "{{user.region}}"
aws events remove-targets --rule "{{user.rule_name}}" --event-bus-name "{{user.bus_name}}" --ids "{{user.target_id}}" \
  --region "{{user.region}}" --output json
aws events delete-rule --name "{{user.rule_name}}" --event-bus-name "{{user.bus_name}}" --region "{{user.region}}" --output json
```

### Delete Event Bus

**Safety Gate**: `confirm=DELETE_BUS {{user.bus_name}}`. Must delete all rules first (EB2).
```bash
aws events list-rules --event-bus-name "{{user.bus_name}}" --region "{{user.region}}"
# Delete each rule (apply EB1 per rule above)
aws events delete-event-bus --name "{{user.bus_name}}" --region "{{user.region}}" --output json
```

### Create Schedule (Scheduler)

```bash
aws scheduler create-schedule \
  --name "{{user.schedule_name}}" \
  --schedule-expression "rate(5 minutes)" \
  --target '{"Arn":"{{user.target_arn}}","RoleArn":"{{user.target_role_arn}}"}' \
  --flexible-time-window '{"Mode":"OFF"}' \
  --region "{{user.region}}" --output json
```

### Delete Schedule

**Safety Gate**: `confirm=DELETE_SCHEDULE {{user.schedule_name}}`
```bash
aws scheduler delete-schedule --name "{{user.schedule_name}}" --region "{{user.region}}" --output json
```

### Create Pipe

```bash
aws pipes create-pipe \
  --name "{{user.pipe_name}}" \
  --source "{{user.pipe_source}}" \
  --target "{{user.target_arn}}" \
  --role-arn "{{user.target_role_arn}}" \
  --region "{{user.region}}" --output json
```

### Delete Pipe

**Safety Gate**: `confirm=DELETE_PIPE {{user.pipe_name}}`
```bash
aws pipes delete-pipe --name "{{user.pipe_name}}" --region "{{user.region}}" --output json
```

### Create Archive

```bash
aws events create-archive \
  --archive-name "{{user.archive_name}}" \
  --event-source-arn "{{user.bus_arn}}" \
  --retention-days 7 \
  --region "{{user.region}}" --output json
```

### Delete Archive

**Safety Gate**: `confirm=DELETE_ARCHIVE {{user.archive_name}}`. Irreversible data loss (EB6).
```bash
aws events delete-archive --archive-name "{{user.archive_name}}" --region "{{user.region}}" --output json
```

### Create API Destination + Connection

```bash
# Step 1: Connection
aws events create-connection --name "{{user.conn_name}}" --authorization-type API_KEY \
  --auth-parameters '{"ApiKeyAuthParameters":{"ApiKeyName":"X-API-Key","ApiKeyValue":"{{user.api_key}}"}}' \
  --region "{{user.region}}" --output json
# Step 2: API destination
aws events create-api-destination --name "{{user.api_dest_name}}" --connection-arn "{{output.conn_arn}}" \
  --invocation-endpoint "{{user.api_dest_endpoint}}" --http-method POST \
  --region "{{user.region}}" --output json
```

### Delete API Destination / Connection

**Safety Gates**: `confirm=DELETE_API_DEST {{user.api_dest_name}}` / `confirm=DELETE_CONNECTION {{user.conn_name}}`
- `delete-connection`: verify no API destinations reference it first (EB3)
- `delete-api-destination`: verify no rules reference it

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded event bus limits/rule quotas — use `list-event-buses` / `describe-rule`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## Quality Gate (GCL)

Full spec: [`aws-skill-generator/references/gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md).
5-dimension rubric (Safety=0→ABORT) in [`references/rubric.md`](references/rubric.md).

| Operation | GCL | Notes |
|---|---|---|
| `delete-rule` | required | Must remove targets first; `confirm=DELETE_RULE <name>` |
| `delete-event-bus` | required | Delete all rules first; `confirm=DELETE_BUS <name>` |
| `delete-api-destination` | required | `confirm=DELETE_API_DEST <name>` |
| `delete-connection` | required | May break API destinations using it; `confirm=DELETE_CONNECTION <name>` |
| `delete-archive` | required | Irrecoverable; events lost; `confirm=DELETE_ARCHIVE <name>` |
| `remove-targets` | required | `confirm=REMOVE_TARGETS <rule>` |
| `delete-schedule` | required | `confirm=DELETE_SCHEDULE <name>` |
| `delete-pipe` | required | Stops event flow; `confirm=DELETE_PIPE <name>` |
| `put-rule` (modify) | recommended | Can change event routing |
| `put-event-bus` (policy) | recommended | Broad permission changes |
| All others | not required | Create, describe, list |

Prompt templates: [`references/prompt-templates.md`](references/prompt-templates.md)

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

