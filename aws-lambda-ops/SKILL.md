---
name: aws-lambda-ops
description: >-
  Use when the user needs to create, deploy, configure, or manage AWS Lambda
  serverless functions; work with Lambda layers, versions, and aliases; set up
  event source mappings with SQS, SNS, DynamoDB, or Kinesis; configure function
  settings like memory, timeout, runtime, and environment variables; invoke
  functions synchronously or asynchronously; configure provisioned concurrency
  or dead-letter queues for error handling; or troubleshoot Lambda invocation
  errors, even if they don't say "Lambda" and instead say "deploy a serverless
  function", "set up an event-driven function", "configure a Lambda function",
  "manage function layers", or "create an event source mapping for AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Lambda endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-06-26"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'capacity-forecast']
    produces_facts: ['metric', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS Lambda Ops Skill

AWS Lambda serverless compute operations skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Create Function:   .FunctionArn
# Update Code:       .{FunctionArn,State,Version}
# Update Config:     .{FunctionArn,Timeout,MemorySize,Runtime}
# Invoke:            .StatusCode  (200=sync, 202=async)
# List Functions:    .Functions[].{FunctionName,FunctionArn,Runtime}
# Create ESM:        .UUID
# Publish Layer:     .LayerVersionArn
# Get Function:      .Configuration.{FunctionArn,State,LastModified}
```

## Trigger & Scope

### SHOULD Use When
- User requests Lambda function create/update/delete/invoke
- Layer management operations (publish, list, attach)
- Event source mapping configuration (SQS, SNS, DynamoDB, Kinesis)
- Alias and version management
- Function configuration changes (memory, timeout, runtime, handler)
- Lambda deployment or rollback scenarios
- Troubleshooting Lambda invocation failures

### SHOULD NOT Use When
- API Gateway configuration → out of scope; use API Gateway CLI/SDK directly
- DynamoDB table operations → delegate to: `aws-dynamodb-ops`
- SQS queue management → delegate to: `aws-sqs-ops`
- SNS topic operations → delegate to: `aws-sns-ops`
- IAM role creation → delegate to: `aws-iam-ops` (only handles execution role attachment)
- VPC configuration → delegate to: `aws-vpc-ops` (Lambda only consumes VPC settings)

### Delegation
| Condition | Skill |
|-----------|-------|
| Event source needs source service (SQS/SNS/DynamoDB) | Delegate to respective skill for source setup |
| IAM execution role needed | Request from `aws-iam-ops`, attach in Lambda skill |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | MUST be set; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | MUST be set; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Optional; default per skill |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temp creds |
| `{{user.function_name}}` | User input | Ask once; validate format |
| `{{user.runtime}}` | User input | Ask once; validate supported runtime |
| `{{user.handler}}` | User input | Ask once; format: module.handler |
| `{{user.code_location}}` | User input | S3 bucket/key or local zip path |
| `{{user.execution_role_arn}}` | User input | Must be valid IAM role ARN |

**Never** ask for AWS credentials. **Never** hardcode secrets.

## Execution Flow Pattern

```
Pre-flight → Execute → Validate → Recover
```

**Pre-flight**: `aws --version` + `aws sts get-caller-identity`. Verify function count < account limit, code size < 75MB (zipped). For event source mapping, verify source resource exists.

**CLI (primary)**: `aws lambda [command] --region {{r.region}} --output json` — see [references/aws-cli-usage.md](references/aws-cli-usage.md).

**boto3 (fallback)**: After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

**Validate**: Wait for State=Active (create) or Successful (update) — max 300s. Invocation: StatusCode=200 (sync) or 202 (async). Event source: State=Enabled.

**Common Recovery**:
| Error | Action |
|-------|--------|
| InvalidParameterValue (400) | Fix args; retry once |
| ResourceNotFoundException | HALT; verify resource exists |
| CodeStorageExceededException | HALT; clean unused versions/layers |
| ThrottlingException (429) | Backoff, retry 3x |
| ServiceException (5xx) | Retry 3x; HALT |

## Safety Gates

### Destructive Operations
```
⚠️ DESTRUCTIVE: {{operation}} will permanently remove {{user.function_name}}.
All versions, aliases, and event source mappings will be deleted.
Proceed? [yes/no]:
```

| Action | Gate Required |
|--------|---------------|
| delete-function | Human confirmation |
| delete-event-source-mapping | Human confirmation |
| delete-layer-version | Human confirmation |

## Execution Examples

### Create Function
```bash
aws lambda create-function \
  --function-name {{user.function_name}} --runtime {{user.runtime}} \
  --role {{user.execution_role_arn}} --handler {{user.handler}} \
  --code S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --timeout {{user.timeout}} --memory-size {{user.memory_size}}
```

### Update Function Code
```bash
aws lambda update-function-code \
  --function-name {{user.function_name}} \
  --s3-bucket {{user.s3_bucket}} --s3-key {{user.s3_key}} --publish
```

### Invoke Function
```bash
aws lambda invoke --function-name {{user.function_name}} \
  --invocation-type RequestResponse --payload '{{user.payload}}' response.json
# Async: --invocation-type Event
```

### Create Event Source Mapping
```bash
aws lambda create-event-source-mapping \
  --function-name {{user.function_name}} --event-source-arn {{user.source_arn}} \
  --batch-size {{user.batch_size}} --maximum-batching-window-in-seconds {{user.batch_window}}
```

### Publish Layer Version
```bash
aws lambda publish-layer-version \
  --layer-name {{user.layer_name}} --description "{{user.layer_desc}}" \
  --content S3Bucket={{user.s3_bucket}},S3Key={{user.s3_key}} \
  --compatible-runtimes {{user.runtime1}} {{user.runtime2}}
```

## Validation Criteria

| Operation | Success Indicator | JSON Path |
|-----------|-------------------|-----------|
| create-function | State = Active | `.State` |
| update-function-code | State = Successful | `.State` |
| invoke (sync) | StatusCode = 200 | `.StatusCode` |
| invoke (async) | StatusCode = 202 | `.StatusCode` |
| create-event-source-mapping | State = Enabled | `.State` |
| publish-version | Version number returned | `.Version` |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded runtimes/limits — use `list-functions` / `get-function-configuration`
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
- [Integration Setup](../aws-skill-generator/references/integration.md)
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-lambda-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace
(exact format `confirm=<OPERATION> <resource>`):

- `delete-function` — **IRREVERSIBLE**; pre-flight: `get-function`
  (state must be `Active`) + `list-event-source-mappings` (refuse if
  non-empty without `confirm=DELETE_FUNCTION_WITH_TRIGGERS <name>`)
- `delete-event-source-mapping`
- `delete-layer-version`
- `delete-function-url-config`
- `delete-function-event-invoke-config`
- `delete-function-code-signing-config`
- `delete-function-concurrency` / `delete-provisioned-concurrency-config`
- `put-function-concurrency=0` (effectively stops function)
- `update-function-configuration` with runtime / VPC / role change
- `remove-permission`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource
echo-back), A9 (no env-var values / no literal secrets / no Lambda code
in trace; Secrets Manager / SSM ARN only), A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.

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

